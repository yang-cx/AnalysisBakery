from pathlib import Path
import re
import sys


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def read(path: Path) -> str:
    assert path.exists(), f"Missing expected file: {path}"
    return path.read_text()


def main() -> int:
    config_path = Path("/logs/artifacts/FitExample.local.config")
    starter_path = Path("/app/FitExample.config")
    input_dir = Path("/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Histo")
    hist_log_path = Path("/logs/artifacts/trexfitter_h.log")
    workspace_log_path = Path("/logs/artifacts/trexfitter_w.log")
    fit_log_path = Path("/logs/artifacts/trexfitter_f.log")
    hist_exitcode_path = Path("/logs/artifacts/trexfitter_h.exitcode")
    workspace_exitcode_path = Path("/logs/artifacts/trexfitter_w.exitcode")
    fit_exitcode_path = Path("/logs/artifacts/trexfitter_f.exitcode")
    outputs_list_path = Path("/logs/artifacts/trexfitter_outputs.txt")
    hist_file = Path("/logs/artifacts/FitExample_histos.root")
    workspace_file = Path("/logs/artifacts/FitExample_combined_FitExample_model.root")
    fit_results_file = Path("/logs/artifacts/FitExample_fit_results.root")
    fit_summary_file = Path("/logs/artifacts/FitExample_fit_summary.txt")

    text = read(config_path)
    starter_text = read(starter_path)
    hist_log = strip_ansi(read(hist_log_path))
    workspace_log = strip_ansi(read(workspace_log_path))
    fit_log = strip_ansi(read(fit_log_path))
    hist_exitcode = read(hist_exitcode_path).strip()
    workspace_exitcode = read(workspace_exitcode_path).strip()
    fit_exitcode = read(fit_exitcode_path).strip()
    outputs_list = read(outputs_list_path)

    assert input_dir.exists(), f"Missing mounted input directory: {input_dir}"
    for root_file in ["data.root", "bkg1.root", "bkg2.root", "sig.root"]:
        assert (input_dir / root_file).exists(), f"Missing input file: {root_file}"

    assert 'Job: "FitExample"' in text
    assert 'POI: "SigXsecOverSM"' in text
    assert "ReadFrom: HIST" in text
    assert 'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Histo"' in text
    assert "root://eosuser.cern.ch" not in text
    assert "LoggingFormat:" not in text
    assert 'HistoPath: "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Histo"' in starter_text
    assert "LoggingFormat: NONE" in starter_text
    assert 'Region: "SR_1"' in text
    assert 'Region: "SR_2"' in text
    assert 'Region: "VR"' in text
    assert 'Sample: "Data"' in text
    assert 'Sample: "Signal"' in text
    assert 'Systematic: "JES"' in text
    assert 'HistoNameSufDown: "_jesDown"' in text
    assert "Symmetrisation: TWOSIDED" in text
    assert "Symmetrisation: ONESIDED" not in text
    assert 'NormFactor: "Bkg2Floating",1,0.5,1.8' in text

    assert hist_exitcode == "0", hist_log
    assert workspace_exitcode == "0", workspace_log
    assert fit_exitcode == "0", fit_log
    assert hist_file.exists(), f"Missing collected histogram file: {hist_file}"
    assert workspace_file.exists(), f"Missing collected workspace file: {workspace_file}"
    assert fit_results_file.exists(), f"Missing collected fit results file: {fit_results_file}"
    assert fit_summary_file.exists(), f"Missing collected fit summary file: {fit_summary_file}"
    assert hist_file.stat().st_size > 0, "Histogram ROOT file is empty"
    assert workspace_file.stat().st_size > 0, "Workspace ROOT file is empty"
    assert fit_results_file.stat().st_size > 0, "Fit results ROOT file is empty"
    assert fit_summary_file.stat().st_size > 0, "Fit summary file is empty"

    assert "Successfully read config file." in hist_log, hist_log
    assert "Reading histograms..." in hist_log, hist_log
    assert "Creating/updating file FitExample/Histograms/FitExample_histos.root" in hist_log, hist_log
    assert "Creating workspace..." in workspace_log, workspace_log
    assert "Exporting to RooStats..." in workspace_log, workspace_log
    assert "FIT FINALIZED SUCCESSFULLY" in fit_log, fit_log
    assert "SigXsecOverSM" in fit_log, fit_log
    assert "Bkg2Floating" in hist_log or "Bkg2Floating" in fit_log, fit_log
    assert "root://eosuser.cern.ch" not in hist_log
    assert "root://eosuser.cern.ch" not in workspace_log
    assert "root://eosuser.cern.ch" not in fit_log
    assert "cannot find input file" not in hist_log.lower(), hist_log
    assert "cannot find input file" not in workspace_log.lower(), workspace_log
    assert "HistFactory - Exception" not in fit_log, fit_log

    assert "/tmp/FitExample/Histograms/FitExample_histos.root" in outputs_list, outputs_list
    assert "/tmp/FitExample/RooStats/FitExample_combined_FitExample_model.root" in outputs_list, outputs_list
    assert "/tmp/FitExample/Fits/FitExample.root" in outputs_list, outputs_list

    return 0


if __name__ == "__main__":
    sys.exit(main())
