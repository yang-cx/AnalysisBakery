#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

template_path = Path("/app/template_hyy_config.config")
path = Path("/tmp/hyy_config.config")
text = template_path.read_text()

region_insert = '''Region: "cat_2jet"
  Type: SIGNAL
  HistoName: "cat_2jet"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "2-jet VBF-enhanced"
  ShortLabel: "cat_2jet"

Region: "cat_central_lowptt"
  Type: SIGNAL
  HistoName: "cat_central_lowptt"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "central photons, low p_{Tt}"
  ShortLabel: "cat_central_lowptt"

Region: "cat_central_highptt"
  Type: SIGNAL
  HistoName: "cat_central_highptt"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "central photons, high p_{Tt}"
  ShortLabel: "cat_central_highptt"

Region: "cat_rest_lowptt"
  Type: SIGNAL
  HistoName: "cat_rest_lowptt"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "rest photons, low p_{Tt}"
  ShortLabel: "cat_rest_lowptt"

Region: "cat_rest_highptt"
  Type: SIGNAL
  HistoName: "cat_rest_highptt"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "rest photons, high p_{Tt}"
  ShortLabel: "cat_rest_highptt"

Region: "cat_transition"
  Type: SIGNAL
  HistoName: "cat_transition"
  VariableTitle: "m_{#gamma#gamma} [GeV]"
  Label: "transition photons"
  ShortLabel: "cat_transition"
'''

sample_insert = '''Sample: "Data"
  Type: DATA

Sample: "diphoton"
  Type: BACKGROUND
  Title: "#gamma#gamma continuum"
  FillColor: 616
  LineColor: 1
  UseMCstat: FALSE

Sample: "ggH"
  Type: SIGNAL
  Title: "ggH, H#rightarrow#gamma#gamma"
  FillColor: 2
  LineColor: 2
  UseMCstat: FALSE

Sample: "VBFH"
  Type: SIGNAL
  Title: "VBF H, H#rightarrow#gamma#gamma"
  FillColor: 4
  LineColor: 4
  UseMCstat: FALSE

Sample: "WH"
  Type: SIGNAL
  Title: "WH, H#rightarrow#gamma#gamma"
  FillColor: 8
  LineColor: 8
  UseMCstat: FALSE

Sample: "ZH"
  Type: SIGNAL
  Title: "ZH, H#rightarrow#gamma#gamma"
  FillColor: 9
  LineColor: 9
  UseMCstat: FALSE

Sample: "ttH"
  Type: SIGNAL
  Title: "ttH, H#rightarrow#gamma#gamma"
  FillColor: 3
  LineColor: 3
  UseMCstat: FALSE
'''

text = text.replace(
    '  % Configure this job to read the prepared histogram cache from /histograms.\n',
    '  ReadFrom: HIST\n'
    '  InputFolder: "/histograms/hyy/Histograms/"\n'
    '  SplitHistoFiles: TRUE\n',
)
text = text.replace(
    '% Add all signal regions for this category model here.\n'
    '% Use histogram names that match the cache contents and provide coherent labels.\n',
    region_insert + '\n',
)
text = text.replace(
    '% Add the observed data, diphoton continuum background, and Higgs production\n'
    '% samples available in the histogram cache here.\n',
    sample_insert + '\n',
)

path.write_text(text)
print(f"Updated {path}")
PY
