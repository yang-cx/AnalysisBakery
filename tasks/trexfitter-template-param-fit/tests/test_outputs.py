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
    config = read(Path("/logs/artifacts/FitExampleTemplate_1D.local.config"))
    outputs = read(Path("/logs/artifacts/trexfitter_outputs.txt"))
    parametrization = read(Path("/logs/artifacts/Parametrization.txt"))

    assert 'Job: "FitExampleTemplate_1D"' in config
    assert 'POI: "topMass"' in config
    assert 'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Template"' in config
    assert "Morphing: morphing" in config
    assert "Template: Signal_1p0_172p5@topMass:170" in config
    assert "Template: topMass:172.5" in config
    assert "FitFunction: QUADRATIC" in config
    assert "ParamLimits: Signal_1p0_172p5@SR_emu@0:0:-10:10" in config
    assert "ParamStartValue: Signal_1p0_172p5@SR_emu@0:0:1" in config
    assert "root://eosuser.cern.ch" not in config
    assert "LoggingFormat:" not in config
    assert "topMass" in parametrization
    assert "topMass*topMass" in parametrization

    for root_file in ["Pseudodata.root", "Bkg.root", "ttbar.root"]:
        assert Path("/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Template", root_file).exists()

    logs = {}
    for step in ["h", "t", "w", "f"]:
        logs[step] = strip_ansi(read(Path(f"/logs/artifacts/trexfitter_{step}.log")))
        assert read(Path(f"/logs/artifacts/trexfitter_{step}.exitcode")).strip() == "0", logs[step]
        assert "cannot find input file" not in logs[step].lower(), logs[step]
        assert "Failed to read the config file" not in logs[step], logs[step]

    assert "Creating/updating file FitExampleTemplate_1D/Histograms/FitExampleTemplate_1D_histos.root" in logs["h"]
    assert "Parametrization.txt" in logs["w"], logs["w"]
    assert "Creating workspace" in logs["w"], logs["w"]
    assert "FIT FINALIZED SUCCESSFULLY" in logs["f"], logs["f"]
    assert "topMass" in logs["f"], logs["f"]

    for artifact in [
        "FitExampleTemplate_1D_histos.root",
        "Parametrization.txt",
        "FitExampleTemplate_1D_combined_FitExampleTemplate_1D_model.root",
        "FitExampleTemplate_1D.root",
        "FitExampleTemplate_1D.txt",
        "FitExampleTemplate_1D_errDecomp_topMass.txt",
    ]:
        assert_nonempty(Path("/logs/artifacts", artifact))

    assert "/tmp/FitExampleTemplate_1D/Templates/Parametrization.txt" in outputs
    assert "/tmp/FitExampleTemplate_1D/RooStats/FitExampleTemplate_1D_combined_FitExampleTemplate_1D_model.root" in outputs
    assert "/tmp/FitExampleTemplate_1D/Fits/FitExampleTemplate_1D.root" in outputs
    return 0


if __name__ == "__main__":
    sys.exit(main())
