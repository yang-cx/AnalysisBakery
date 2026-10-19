from pathlib import Path
import re
import sys


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def read(path: Path) -> str:
    assert path.exists(), f"Missing expected file: {path}"
    return path.read_text()


def assert_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing expected artifact: {path}"
    assert path.stat().st_size > 0, f"Empty artifact: {path}"


def block(text: str, header: str) -> str:
    start = text.index(header)
    match = re.search(
        r"\n(?:Job|Fit|Limit|Region|Sample|NormFactor|Systematic|Morphing|Unfolding): ",
        text[start + 1 :],
    )
    end = start + 1 + match.start() if match else len(text)
    return text[start:end]


def main() -> int:
    config = read(Path("/logs/artifacts/FitExampleNtuple.local.config"))
    starter = read(Path("/app/FitExampleNtuple.config"))
    outputs = read(Path("/logs/artifacts/trexfitter_outputs.txt"))
    region_data = block(config, 'Region: "ljets_5j3b_HT"')
    region_asimov = block(config, 'Region: "ljets_6j4b_BDT"')

    assert 'Job: "FitExampleNtuple"' in config
    assert 'POI: "mu_XS_ttH"' in config
    assert "ReadFrom: NTUP" in config
    assert 'NtuplePaths: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Ntuple"' in config
    assert 'Binning: "AutoBin","TransfoD",3,3' in config
    assert "FitBlind: FALSE" in config
    assert "DataType: DATA" in region_data
    assert "DataType: ASIMOV" in region_asimov
    assert "root://eosuser.cern.ch" not in config
    assert "LoggingFormat:" not in config
    assert "LoggingFormat: NONE" in starter

    for root_file in ["tt_PP8.root", "tt_aMCNloP8.root", "ttH_PP8.root"]:
        assert Path("/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Ntuple", root_file).exists()

    logs = {}
    for step in ["n", "b", "w", "f"]:
        logs[step] = strip_ansi(read(Path(f"/logs/artifacts/trexfitter_{step}.log")))
        assert read(Path(f"/logs/artifacts/trexfitter_{step}.exitcode")).strip() == "0", logs[step]
        assert "cannot find input file" not in logs[step].lower(), logs[step]
        assert "Failed to read the config file" not in logs[step], logs[step]

    assert "Reading ntuples" in logs["n"], logs["n"]
    assert "Creating workspace" in logs["w"], logs["w"]
    assert "Exporting to RooStats" in logs["w"], logs["w"]
    assert "FIT FINALIZED SUCCESSFULLY" in logs["f"], logs["f"]
    assert "mu_XS_ttH" in logs["f"], logs["f"]

    for artifact in [
        "FitExampleNtuple_ljets_5j3b_HT_histos.root",
        "FitExampleNtuple_ljets_6j4b_BDT_histos.root",
        "ljets_5j3b_HT.txt",
        "ljets_6j4b_BDT.txt",
        "FitExampleNtuple_combined_FitExampleNtuple_model.root",
        "FitExampleNtuple_realisticAsimov.root",
        "FitExampleNtuple.root",
        "FitExampleNtuple.txt",
    ]:
        assert_nonempty(Path("/logs/artifacts", artifact))

    assert "/tmp/FitExampleNtuple/Histograms/FitExampleNtuple_ljets_5j3b_HT_histos.root" in outputs
    assert "/tmp/FitExampleNtuple/Histograms/Binnings/ljets_6j4b_BDT.txt" in outputs
    assert "/tmp/FitExampleNtuple/RooStats/FitExampleNtuple_combined_FitExampleNtuple_model.root" in outputs
    assert "/tmp/FitExampleNtuple/RooStats/FitExampleNtuple_realisticAsimov.root" in outputs
    assert "/tmp/FitExampleNtuple/Fits/FitExampleNtuple.root" in outputs
    return 0


if __name__ == "__main__":
    sys.exit(main())
