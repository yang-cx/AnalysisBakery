#!/usr/bin/env python3
"""Download CERN Open Data records 93929 and 93931 reproducibly.

The script refreshes record metadata from the CERN Open Data API, writes a YAML
inventory, and downloads the ROOT payloads from the public EOS XRootD endpoint.
By default it uses ROOT/XRootD's `xrdcp` client for resumable `root://`
transfers; the HTTPS/curl path is kept as a fallback.
"""

from __future__ import print_function

import argparse
import concurrent.futures
import datetime as _datetime
import html
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import zlib

try:
    from urllib.parse import quote
    from urllib.request import urlopen
except ImportError:  # pragma: no cover, Python 2 fallback is not expected.
    from urllib import quote
    from urllib2 import urlopen


DEFAULT_RECORDS = ("93929", "93931")
API_URL = "https://opendata.cern.ch/api/records/{record_id}"
RECORD_URL = "https://opendata.cern.ch/record/{record_id}"
EOS_ROOT_PREFIX = "root://eospublic.cern.ch//"
EOS_HTTPS_PREFIX = "https://eospublic.cern.ch/"
ACTIVE_TRANSFER_PROCS = set()
ACTIVE_TRANSFER_LOCK = threading.Lock()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch CERN Open Data metadata and download records 93929/93931."
    )
    parser.add_argument(
        "--output-dir",
        default="dataset",
        help="Directory for YAML, metadata cache, and downloaded ROOT files.",
    )
    parser.add_argument(
        "--records",
        nargs="+",
        default=list(DEFAULT_RECORDS),
        help="CERN Open Data record IDs to fetch.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write metadata and YAML only; do not download ROOT files.",
    )
    parser.add_argument(
        "--use-cached-metadata",
        action="store_true",
        help="Use dataset/metadata/record_<id>.json instead of fetching the API.",
    )
    parser.add_argument(
        "--verify-checksum",
        action="store_true",
        help="Compute and compare adler32 checksums after download or skip checks.",
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Do not pass --insecure to curl for EOS HTTPS downloads.",
    )
    parser.add_argument(
        "--transfer-backend",
        choices=("xrdcp", "curl"),
        default="xrdcp",
        help="Transfer backend for ROOT payloads. Default: xrdcp.",
    )
    parser.add_argument(
        "--xrdcp-streams",
        type=int,
        default=1,
        help="Number of xrdcp TCP streams per file.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=10,
        help="Number of curl retry attempts per file.",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=30,
        help="Seconds between curl retries.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit downloads to the first N files after metadata generation.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of files to download concurrently.",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help="Only download files whose names contain this substring.",
    )
    return parser.parse_args()


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def fetch_record(record_id):
    url = API_URL.format(record_id=record_id)
    with urlopen(url) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")), raw


def load_record(record_id, metadata_dir, use_cached):
    cache_path = Path(metadata_dir) / ("record_%s.json" % record_id)
    if use_cached:
        if not cache_path.exists():
            raise RuntimeError("cached metadata does not exist: %s" % cache_path)
        raw = cache_path.read_bytes()
        return json.loads(raw.decode("utf-8"))

    record, raw = fetch_record(record_id)
    ensure_dir(metadata_dir)
    cache_path.write_bytes(raw)
    return record


def strip_html(value):
    if not value:
        return ""
    text = re.sub(r"<\s*br\s*/?\s*>", " ", value)
    text = re.sub(r"</\s*p\s*>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(value):
    text = re.sub(r"[^A-Za-z0-9]+", "_", value)
    return re.sub(r"_+", "_", text).strip("_").lower()


def dataset_kind(metadata):
    title = metadata.get("title", "").lower()
    secondary_types = [
        str(item).lower() for item in metadata.get("type", {}).get("secondary", [])
    ]
    if "simulated" in secondary_types or "mc simulation" in title:
        return "mc"
    return "data"


def skim_label(metadata, methodology):
    title = metadata.get("title", "")
    for value in (title, methodology):
        match = re.search(r"\b([A-Za-z0-9]+)\s+skim\b", value)
        if match:
            return match.group(1)
    return "unknown_skim"


def run_label(metadata):
    title = metadata.get("title", "")
    match = re.search(r"\bRun\s+([0-9]+)\b", title, flags=re.IGNORECASE)
    if match:
        return "run%s" % match.group(1)

    years = [str(year) for year in metadata.get("run_period", [])]
    if any(year in years for year in ("2015", "2016", "2017", "2018")):
        return "run2"
    return "unknown_run"


def year_label(metadata):
    years = metadata.get("run_period") or metadata.get("date_created") or []
    years = [str(year) for year in years]
    return "_".join(years) if years else "unknown_year"


def record_directory_name(metadata, methodology):
    parts = [
        "atlas",
        dataset_kind(metadata),
        skim_label(metadata, methodology),
        run_label(metadata),
        year_label(metadata),
    ]
    return slugify("_".join(parts))


def bytes_to_gib(size):
    return round(float(size) / float(1024 ** 3), 3)


def utc_timestamp():
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def root_uri_to_https(uri):
    if uri.startswith(EOS_ROOT_PREFIX):
        eos_path = uri[len(EOS_ROOT_PREFIX) :]
        return EOS_HTTPS_PREFIX + quote(eos_path, safe="/._-")
    return uri


def split_checksum(checksum):
    if not checksum or ":" not in checksum:
        return "", checksum or ""
    return checksum.split(":", 1)


def build_record_inventory(record, output_dir):
    metadata = record["metadata"]
    record_id = str(record.get("id") or metadata.get("recid"))
    files = metadata.get("_files") or metadata.get("files") or []
    distribution = metadata.get("distribution", {})
    methodology = strip_html(metadata.get("methodology", {}).get("description", ""))
    usage = strip_html(metadata.get("usage", {}).get("description", ""))
    abstract = strip_html(metadata.get("abstract", {}).get("description", ""))
    directory_name = record_directory_name(metadata, methodology)

    skim_selection = ""
    match = re.search(r"selection was applied:\s*(.*)", methodology)
    if match:
        skim_selection = match.group(1).strip()

    file_entries = []
    for item in files:
        name = item["key"]
        checksum_type, checksum_value = split_checksum(item.get("checksum", ""))
        local_path = str(Path(output_dir) / directory_name / name)
        file_entries.append(
            {
                "name": name,
                "size_bytes": int(item.get("size", 0)),
                "size_gib": bytes_to_gib(int(item.get("size", 0))),
                "checksum": item.get("checksum", ""),
                "checksum_type": checksum_type,
                "checksum_value": checksum_value,
                "availability": item.get("availability", ""),
                "local_path": local_path,
                "download_url": root_uri_to_https(item.get("uri", "")),
                "root_uri": item.get("uri", ""),
                "bucket": item.get("bucket", metadata.get("_bucket", "")),
                "file_id": item.get("file_id", ""),
                "version_id": item.get("version_id", ""),
            }
        )

    total_size = sum(item["size_bytes"] for item in file_entries)
    return {
        "record_id": record_id,
        "directory_name": directory_name,
        "record_url": RECORD_URL.format(record_id=record_id),
        "api_url": API_URL.format(record_id=record_id),
        "title": metadata.get("title", ""),
        "dataset_kind": dataset_kind(metadata),
        "skim": skim_label(metadata, methodology),
        "run": run_label(metadata),
        "years": year_label(metadata),
        "citation": "%s (2025). %s. CERN Open Data Portal. DOI: %s"
        % (
            metadata.get("collaboration", {}).get("name", "ATLAS collaboration"),
            metadata.get("title", ""),
            metadata.get("doi", ""),
        ),
        "doi": metadata.get("doi", ""),
        "doi_url": "https://doi.org/%s" % metadata.get("doi", ""),
        "publisher": metadata.get("publisher", ""),
        "collaboration": metadata.get("collaboration", {}).get("name", ""),
        "experiment": metadata.get("experiment", []),
        "type": metadata.get("type", {}),
        "accelerator": metadata.get("accelerator", ""),
        "collision_information": metadata.get("collision_information", {}),
        "run_period": metadata.get("run_period", []),
        "date_created": metadata.get("date_created", []),
        "date_published": metadata.get("date_published", ""),
        "date_reprocessed": metadata.get("date_reprocessed", ""),
        "availability": metadata.get("availability", ""),
        "license": metadata.get("license", {}),
        "collections": metadata.get("collections", []),
        "categories": metadata.get("categories", {}),
        "distribution": {
            "formats": distribution.get("formats", []),
            "number_events": distribution.get("number_events", 0),
            "number_files": distribution.get("number_files", len(file_entries)),
            "size_bytes": distribution.get("size", total_size),
            "size_gib": bytes_to_gib(distribution.get("size", total_size)),
        },
        "availability_details": metadata.get("_availability_details", {}),
        "abstract": abstract,
        "methodology": methodology,
        "skimming_selection": skim_selection,
        "usage": usage,
        "usage_links": metadata.get("usage", {}).get("links", []),
        "relations": metadata.get("relations", []),
        "download_directory": str(Path(output_dir) / directory_name),
        "files": file_entries,
    }


def build_inventory(records, output_dir):
    record_entries = [build_record_inventory(record, output_dir) for record in records]
    total_files = sum(len(record["files"]) for record in record_entries)
    total_size = sum(
        sum(item["size_bytes"] for item in record["files"]) for record in record_entries
    )
    return {
        "generated_at_utc": utc_timestamp(),
        "source": "CERN Open Data Portal",
        "source_record_ids": [record["record_id"] for record in record_entries],
        "download_note": (
            "ROOT payloads are downloaded from each record's root:// EOS URI "
            "using ROOT/XRootD xrdcp by default. HTTPS URLs are retained for "
            "curl fallback workflows."
        ),
        "total": {
            "records": len(record_entries),
            "files": total_files,
            "size_bytes": total_size,
            "size_gib": bytes_to_gib(total_size),
        },
        "records": record_entries,
    }


def yaml_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=True)


def yaml_lines(value, indent=0):
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [prefix + "{}"]
        lines = []
        for key, child in value.items():
            key_text = str(key)
            if isinstance(child, (dict, list)):
                if not child:
                    lines.append(prefix + key_text + ": " + ("[]" if isinstance(child, list) else "{}"))
                else:
                    lines.append(prefix + key_text + ":")
                    lines.extend(yaml_lines(child, indent + 2))
            else:
                lines.append(prefix + key_text + ": " + yaml_scalar(child))
        return lines
    if isinstance(value, list):
        if not value:
            return [prefix + "[]"]
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                if not item:
                    lines.append(prefix + "- " + ("[]" if isinstance(item, list) else "{}"))
                else:
                    lines.append(prefix + "-")
                    lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(prefix + "- " + yaml_scalar(item))
        return lines
    return [prefix + yaml_scalar(value)]


def write_yaml(path, inventory):
    text = "\n".join(yaml_lines(inventory)) + "\n"
    Path(path).write_text(text, encoding="utf-8")


def adler32_file(path):
    checksum = 1
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum = zlib.adler32(chunk, checksum)
    return "%08x" % (checksum & 0xFFFFFFFF)


def file_is_complete(path, expected_size, expected_checksum, verify_checksum):
    if not path.exists():
        return False
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        return False
    if verify_checksum and expected_checksum.startswith("adler32:"):
        expected_value = expected_checksum.split(":", 1)[1].lower()
        actual_value = adler32_file(path)
        if actual_value != expected_value:
            raise RuntimeError(
                "checksum mismatch for %s: expected %s, got %s"
                % (path, expected_value, actual_value)
            )
    return True


def terminate_active_transfers():
    with ACTIVE_TRANSFER_LOCK:
        procs = list(ACTIVE_TRANSFER_PROCS)
    for proc in procs:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except OSError:
                pass


def run_transfer_command(command):
    proc = subprocess.Popen(command, preexec_fn=os.setsid)
    with ACTIVE_TRANSFER_LOCK:
        ACTIVE_TRANSFER_PROCS.add(proc)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            pass
        raise
    finally:
        with ACTIVE_TRANSFER_LOCK:
            ACTIVE_TRANSFER_PROCS.discard(proc)


def run_xrdcp_download(uri, destination, expected_checksum, args, quiet=False):
    xrdcp = shutil.which("xrdcp")
    if not xrdcp:
        raise RuntimeError(
            "xrdcp was not found on PATH; activate an environment with ROOT/XRootD "
            "or use --transfer-backend curl"
        )
    if args.xrdcp_streams < 1:
        raise RuntimeError("--xrdcp-streams must be at least 1")

    command = [
        xrdcp,
        "--retry",
        str(args.retries),
        "--streams",
        str(args.xrdcp_streams),
        "--nopbar",
    ]
    if destination.exists():
        command.extend(["--continue", "--retry-policy", "continue"])
    else:
        command.append("--force")
    checksum_type, checksum_value = split_checksum(expected_checksum)
    if checksum_type == "adler32" and checksum_value:
        command.extend(["--cksum", "adler32:%s" % checksum_value, "--rm-bad-cksum"])
    if quiet:
        command.append("--silent")
    command.extend([uri, str(destination)])
    return run_transfer_command(command)


def run_curl_download(url, destination, args, quiet=False):
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl was not found on PATH")
    command = [
        curl,
        "-L",
        "--fail",
        "--show-error",
        "--retry",
        str(args.retries),
        "--retry-delay",
        str(args.retry_delay),
        "--continue-at",
        "-",
        "--output",
        str(destination),
    ]
    if quiet:
        command.insert(1, "--silent")
    if not args.verify_tls:
        command.insert(1, "--insecure")
    command.append(url)
    return run_transfer_command(command)


def iter_download_files(inventory, args):
    count = 0
    for record in inventory["records"]:
        for item in record["files"]:
            if args.pattern and args.pattern not in item["name"]:
                continue
            if args.max_files is not None and count >= args.max_files:
                return
            count += 1
            yield record, item


def download_one_file(task):
    record, item, args, quiet = task
    destination = Path(item["local_path"])
    ensure_dir(destination.parent)
    expected_size = int(item["size_bytes"])
    expected_checksum = item.get("checksum", "")

    if destination.exists() and destination.stat().st_size > expected_size:
        raise RuntimeError(
            "local file is larger than expected, refusing to resume: %s" % destination
        )

    if file_is_complete(
        destination, expected_size, expected_checksum, args.verify_checksum
    ):
        return "ok: %s" % destination

    print(
        "download: %s via %s" % (destination, args.transfer_backend),
        flush=True,
    )
    if args.transfer_backend == "xrdcp":
        rc = run_xrdcp_download(
            item["root_uri"], destination, expected_checksum, args, quiet=quiet
        )
    else:
        rc = run_curl_download(item["download_url"], destination, args, quiet=quiet)
    if rc != 0:
        raise RuntimeError(
            "%s failed with exit code %s for %s"
            % (args.transfer_backend, rc, item["name"])
        )

    if not file_is_complete(
        destination, expected_size, expected_checksum, args.verify_checksum
    ):
        raise RuntimeError("downloaded file has the wrong size: %s" % destination)

    return "done: %s" % destination


def download_files(inventory, args):
    if args.jobs < 1:
        raise RuntimeError("--jobs must be at least 1")

    files = list(iter_download_files(inventory, args))
    if args.jobs == 1:
        for record, item in files:
            print(download_one_file((record, item, args, False)))
        return

    tasks = [(record, item, args, True) for record, item in files]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(download_one_file, task) for task in tasks]
        try:
            for future in concurrent.futures.as_completed(futures):
                print(future.result(), flush=True)
        except KeyboardInterrupt:
            terminate_active_transfers()
            raise


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    metadata_dir = output_dir / "metadata"
    ensure_dir(output_dir)
    ensure_dir(metadata_dir)

    records = [
        load_record(record_id, metadata_dir, args.use_cached_metadata)
        for record_id in args.records
    ]
    inventory = build_inventory(records, str(output_dir))
    yaml_path = output_dir / "records.yaml"
    write_yaml(yaml_path, inventory)
    print("wrote %s" % yaml_path)
    print(
        "inventory: %s records, %s files, %.3f GiB"
        % (
            inventory["total"]["records"],
            inventory["total"]["files"],
            inventory["total"]["size_gib"],
        )
    )

    if args.metadata_only:
        return 0

    download_files(inventory, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
