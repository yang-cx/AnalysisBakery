#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

source = Path("/app/FitExample.config")
target = Path("/tmp/FitExample.local.config")
text = source.read_text()
text = text.replace(
    'HistoPath: "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Histo"',
    'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Histo"',
)
text = text.replace('  LoggingFormat: NONE\n', '')
text = text.replace('%   HistoNameSufDown: "_jesDown"\n', '  HistoNameSufDown: "_jesDown"\n')
text = text.replace('%   Symmetrisation: TwoSided\n', '  Symmetrisation: TWOSIDED\n')
text = text.replace('  Symmetrisation: ONESIDED\n', '')
if 'NormFactor: "Bkg2Floating"' not in text:
    text = text.replace(
        '  HistoFile: "bkg2"\n',
        '  HistoFile: "bkg2"\n  NormFactor: "Bkg2Floating",1,0.5,1.8\n',
    )
target.write_text(text)
print(f"Wrote {target}")
PY
