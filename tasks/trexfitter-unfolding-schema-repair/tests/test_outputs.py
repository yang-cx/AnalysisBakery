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
    config = read(Path("/logs/artifacts/FitExampleUnfolding.local.config"))
    outputs = read(Path("/logs/artifacts/trexfitter_outputs.txt"))

    local_path = "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Unfolding"
    assert 'Job: "FitExampleUnfolding"' in config
    assert "FitType: UNFOLDING" in config
    assert f'HistoPath: "{local_path}"' in config
    assert f'MigrationPath: "{local_path}"' in config
    assert f"TruthDistributionPath: {local_path}" in config
    assert "NumberOfRecoBins: 11" in config
    assert "NumberOfTruthBins: 11" in config
    assert "PruningType: COMBINEDSIGNAL" in config
    assert "UnfoldNormXSec: TRUE" in config
    assert "UnfoldNormXSecBinN: 2" in config
    assert "root://eosuser.cern.ch" not in config
    assert "LoggingFormat:" not in config

    assert Path(local_path, "InputUnfolding.root").exists()

    logs = {}
    for step in ["u", "h", "w", "f"]:
        logs[step] = strip_ansi(read(Path(f"/logs/artifacts/trexfitter_{step}.log")))
        assert read(Path(f"/logs/artifacts/trexfitter_{step}.exitcode")).strip() == "0", logs[step]
        assert "cannot find input file" not in logs[step].lower(), logs[step]
        assert "Failed to read the config file" not in logs[step], logs[step]
        assert "NumberOfRecoBins" not in logs[step] or "ERROR" not in logs[step], logs[step]

    assert "Unfolding" in logs["u"], logs["u"]
    assert "Creating/updating file FitExampleUnfolding/Histograms/FitExampleUnfolding_histos.root" in logs["h"]
    assert "Creating workspace" in logs["w"], logs["w"]
    assert "FIT FINALIZED SUCCESSFULLY" in logs["f"], logs["f"]
    assert "Unfolding_Bin_001_mu" in logs["f"], logs["f"]
    combined_logs = "\n".join(logs.values())
    assert "Adding expression to turn cross section into normalized cross-section" in combined_logs
    assert "normalized cross-section" in combined_logs

    for artifact in [
        "FitExampleUnfolding_histos.root",
        "SR1.txt",
        "FitExampleUnfolding_combined_FitExampleUnfolding_model.root",
        "FitExampleUnfolding_combined_FitExampleUnfolding_withRegularisation.root",
        "FitExampleUnfolding.root",
        "FitExampleUnfolding.txt",
        "Unfolding_UnfoldedResults.txt",
    ]:
        assert_nonempty(Path("/logs/artifacts", artifact))

    assert "/tmp/FitExampleUnfolding/Histograms/FitExampleUnfolding_histos.root" in outputs
    assert "/tmp/FitExampleUnfolding/RooStats/FitExampleUnfolding_combined_FitExampleUnfolding_model.root" in outputs
    assert "/tmp/FitExampleUnfolding/Fits/Unfolding_UnfoldedResults.txt" in outputs
    return 0


if __name__ == "__main__":
    sys.exit(main())
