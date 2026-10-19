from pathlib import Path
import re
import sys


def block_after(text: str, header: str) -> str:
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == header:
            start = idx
            break
    if start is None:
        raise AssertionError(f"Missing block header: {header}")
    out = [lines[start]]
    for line in lines[start + 1 :]:
        if line and not line.startswith(" ") and not line.startswith("%"):
            break
        out.append(line)
    return "\n".join(out)


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def main() -> int:
    config_path = Path("/logs/artifacts/hyy_config.config")
    workspace_log_path = Path("/logs/artifacts/trexfitter_w.log")
    workspace_exitcode_path = Path("/logs/artifacts/trexfitter_w.exitcode")
    fit_log_path = Path("/logs/artifacts/trexfitter_f.log")
    fit_exitcode_path = Path("/logs/artifacts/trexfitter_f.exitcode")
    significance_log_path = Path("/logs/artifacts/trexfitter_s.log")
    significance_exitcode_path = Path("/logs/artifacts/trexfitter_s.exitcode")
    workspace_file = Path("/logs/artifacts/hyy_combined_hyy_model.root")
    fit_results_file = Path("/logs/artifacts/hyy_fit_results.root")
    significance_workspace_file = Path("/logs/artifacts/hyy_significance_workspace.root")
    significance_parameter_file = Path("/logs/artifacts/hyy_significance_parameter.root")
    outputs_list_path = Path("/logs/artifacts/trexfitter_outputs.txt")
    significance_summary_path = Path("/logs/artifacts/significance_summary.txt")
    template_path = Path("/app/template_hyy_config.config")

    assert config_path.exists(), f"Missing collected config file: {config_path}"
    assert template_path.exists(), f"Missing starter template: {template_path}"
    assert workspace_log_path.exists(), f"Missing workspace log: {workspace_log_path}"
    assert workspace_exitcode_path.exists(), f"Missing workspace exit code: {workspace_exitcode_path}"
    assert fit_log_path.exists(), f"Missing fit log: {fit_log_path}"
    assert fit_exitcode_path.exists(), f"Missing fit exit code: {fit_exitcode_path}"
    assert significance_log_path.exists(), f"Missing significance log: {significance_log_path}"
    assert significance_exitcode_path.exists(), f"Missing significance exit code: {significance_exitcode_path}"
    assert workspace_file.exists(), f"Missing workspace output: {workspace_file}"
    assert fit_results_file.exists(), f"Missing fit results output: {fit_results_file}"
    assert significance_workspace_file.exists(), f"Missing significance workspace output: {significance_workspace_file}"
    assert significance_parameter_file.exists(), f"Missing significance parameter output: {significance_parameter_file}"
    assert outputs_list_path.exists(), f"Missing TRExFitter outputs listing: {outputs_list_path}"
    assert significance_summary_path.exists(), f"Missing significance summary: {significance_summary_path}"

    text = config_path.read_text()
    workspace_log = strip_ansi(workspace_log_path.read_text())
    workspace_exitcode = workspace_exitcode_path.read_text().strip()
    fit_log = strip_ansi(fit_log_path.read_text())
    fit_exitcode = fit_exitcode_path.read_text().strip()
    significance_log = strip_ansi(significance_log_path.read_text())
    significance_exitcode = significance_exitcode_path.read_text().strip()
    outputs_list = outputs_list_path.read_text()
    significance_summary = strip_ansi(significance_summary_path.read_text())
    template_text = template_path.read_text()

    assert 'ReadFrom: HIST' in text
    assert 'InputFolder: "/histograms/hyy/Histograms/"' in text
    assert 'SplitHistoFiles: TRUE' in text
    assert 'NtuplePaths:' not in text
    assert 'NtupleFiles:' not in text
    assert 'Selection:' not in text
    assert '% Add all signal regions for this category model here.' in template_text
    assert 'Sample: "Data"' not in template_text
    assert 'Region: "cat_2jet"' not in template_text

    for region_name, label, shortlabel in [
        ("cat_2jet", 'Label: "2-jet VBF-enhanced"', 'ShortLabel: "cat_2jet"'),
        ("cat_central_lowptt", 'Label: "central photons, low p_{Tt}"', 'ShortLabel: "cat_central_lowptt"'),
        ("cat_central_highptt", 'Label: "central photons, high p_{Tt}"', 'ShortLabel: "cat_central_highptt"'),
        ("cat_rest_lowptt", 'Label: "rest photons, low p_{Tt}"', 'ShortLabel: "cat_rest_lowptt"'),
        ("cat_rest_highptt", 'Label: "rest photons, high p_{Tt}"', 'ShortLabel: "cat_rest_highptt"'),
        ("cat_transition", 'Label: "transition photons"', 'ShortLabel: "cat_transition"'),
    ]:
        block = block_after(text, f'Region: "{region_name}"')
        assert "Type: SIGNAL" in block, block
        assert f'HistoName: "{region_name}"' in block, block
        assert 'VariableTitle: "m_{#gamma#gamma} [GeV]"' in block, block
        assert label in block, block
        assert shortlabel in block, block

    for sample_name, sample_type, extra_checks in [
        ("Data", "DATA", []),
        ("diphoton", "BACKGROUND", ['Title: "#gamma#gamma continuum"', "FillColor: 616", "LineColor: 1", "UseMCstat: FALSE"]),
        ("ggH", "SIGNAL", ['Title: "ggH, H#rightarrow#gamma#gamma"', "FillColor: 2", "LineColor: 2", "UseMCstat: FALSE"]),
        ("VBFH", "SIGNAL", ['Title: "VBF H, H#rightarrow#gamma#gamma"', "FillColor: 4", "LineColor: 4", "UseMCstat: FALSE"]),
        ("WH", "SIGNAL", ['Title: "WH, H#rightarrow#gamma#gamma"', "FillColor: 8", "LineColor: 8", "UseMCstat: FALSE"]),
        ("ZH", "SIGNAL", ['Title: "ZH, H#rightarrow#gamma#gamma"', "FillColor: 9", "LineColor: 9", "UseMCstat: FALSE"]),
        ("ttH", "SIGNAL", ['Title: "ttH, H#rightarrow#gamma#gamma"', "FillColor: 3", "LineColor: 3", "UseMCstat: FALSE"]),
    ]:
        block = block_after(text, f'Sample: "{sample_name}"')
        assert f"Type: {sample_type}" in block, block
        for expected_line in extra_checks:
            assert expected_line in block, block

    for nf_name, region_name in [
        ("mu_yy_cat_central_lowptt", "cat_central_lowptt"),
        ("mu_yy_cat_central_highptt", "cat_central_highptt"),
        ("mu_yy_cat_transition", "cat_transition"),
    ]:
        block = block_after(text, f'NormFactor: "{nf_name}"')
        assert "Samples: diphoton" in block, block
        assert f"Regions: {region_name}" in block, block
        assert "Nominal: 1" in block, block
        assert "Max: 10" in block, block

    assert workspace_exitcode == "0", workspace_log
    assert fit_exitcode == "0", fit_log
    assert significance_exitcode == "0", significance_log
    assert workspace_file.stat().st_size > 0, "Workspace ROOT file is empty"
    assert fit_results_file.stat().st_size > 0, "Fit results ROOT file is empty"
    assert significance_workspace_file.stat().st_size > 0, "Significance workspace ROOT file is empty"
    assert significance_parameter_file.stat().st_size > 0, "Significance parameter ROOT file is empty"

    assert "Successfully read config file." in workspace_log, workspace_log
    assert "Reading histograms from file /histograms/hyy/Histograms/hyy_cat_transition_histos.root" in workspace_log, workspace_log
    assert "Creating workspace..." in workspace_log, workspace_log
    assert "Exporting to RooStats..." in workspace_log, workspace_log
    assert "FIT FINALIZED SUCCESSFULLY" in fit_log, fit_log
    assert "mu_yy_cat_transition" in fit_log, fit_log
    assert "mu_H" in fit_log, fit_log
    assert "Extracting significance..." in significance_log, significance_log
    assert "Printing results of the asymptotic significance estimate" in significance_log, significance_log
    assert "Expected significance mu = 1 (median)" in significance_log, significance_log
    assert "Observed significance (median)" in significance_log, significance_log
    assert "Expected significance mu = 1 (median)" in significance_summary, significance_summary
    assert "Observed significance (median)" in significance_summary, significance_summary
    assert "/tmp/hyy/RooStats/hyy_combined_hyy_model.root" in outputs_list, outputs_list
    assert "/tmp/hyy/Fits/hyy.root" in outputs_list, outputs_list
    assert "/tmp/hyy/Significance/Asymptotics/PostSignificanceWS.root" in outputs_list, outputs_list
    assert "/tmp/hyy/Significance/Asymptotics/parameter.root" in outputs_list, outputs_list
    assert "cannot find input file" not in workspace_log.lower(), workspace_log
    assert "HistFactory - Exception" not in fit_log, fit_log
    assert "cannot find input file" not in significance_log.lower(), significance_log

    return 0


if __name__ == "__main__":
    sys.exit(main())
