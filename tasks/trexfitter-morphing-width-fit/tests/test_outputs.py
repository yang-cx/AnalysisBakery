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


def main() -> int:
    config = read(Path("/logs/artifacts/FitExampleMorphing.local.config"))
    outputs = read(Path("/logs/artifacts/trexfitter_outputs.txt"))

    assert 'Job: "FitExampleMorphing"' in config
    assert 'POI: "topWidth"' in config
    assert 'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Morph"' in config
    assert 'Morphing: "topWidth",0.7' in config
    assert 'NormFactor: "topWidth"' in config
    assert "TemplateInterpolationOption: SMOOTHLINEAR" in config
    assert "POIAsimov: topWidth@1.5" in config
    assert 'NormFactor: "bkgScale"' in config
    assert 'Title: "bkgScale"' in config
    assert "Nominal: 1" in config
    assert "Min: 0.5" in config
    assert "Max: 1.5" in config
    assert "Samples: Bkg_SR,Bkg_CR" in config
    assert "root://eosuser.cern.ch" not in config
    assert "LoggingFormat:" not in config

    for root_file in ["Pseudodata.root", "Bkg.root", "ttbar.root"]:
        assert Path("/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Morph", root_file).exists()

    logs = {}
    for step in ["h", "w", "f"]:
        logs[step] = strip_ansi(read(Path(f"/logs/artifacts/trexfitter_{step}.log")))
        assert read(Path(f"/logs/artifacts/trexfitter_{step}.exitcode")).strip() == "0", logs[step]
        assert "cannot find input file" not in logs[step].lower(), logs[step]
        assert "Failed to read the config file" not in logs[step], logs[step]

    assert "Creating/updating file FitExampleMorphing/Histograms/FitExampleMorphing_histos.root" in logs["h"]
    assert "Creating workspace" in logs["w"], logs["w"]
    assert "Exporting to RooStats" in logs["w"], logs["w"]
    assert "FIT FINALIZED SUCCESSFULLY" in logs["f"], logs["f"]
    assert "topWidth" in logs["f"], logs["f"]
    assert "bkgScale" in logs["f"], logs["f"]

    for artifact in [
        "FitExampleMorphing_histos.root",
        "FitExampleMorphing_combined_FitExampleMorphing_model.root",
        "FitExampleMorphing.root",
        "FitExampleMorphing.txt",
        "FitExampleMorphing_errDecomp_topWidth.txt",
    ]:
        assert_nonempty(Path("/logs/artifacts", artifact))

    assert "/tmp/FitExampleMorphing/Histograms/FitExampleMorphing_histos.root" in outputs
    assert "/tmp/FitExampleMorphing/RooStats/FitExampleMorphing_combined_FitExampleMorphing_model.root" in outputs
    assert "/tmp/FitExampleMorphing/Fits/FitExampleMorphing.root" in outputs
    return 0


if __name__ == "__main__":
    sys.exit(main())
