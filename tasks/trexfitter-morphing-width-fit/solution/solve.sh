#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

source = Path("/app/FitExampleMorphing.config")
target = Path("/tmp/FitExampleMorphing.local.config")
text = source.read_text()
text = text.replace(
    'HistoPath: "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Morph"',
    'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Morph"',
)
text = text.replace("  LoggingFormat: NONE\n", "")
text = text.replace("TemplateInterpolationOption: LINEAR", "TemplateInterpolationOption: SMOOTHLINEAR")
text = text.replace("POIAsimov: topWidth@1.32", "POIAsimov: topWidth@1.5")
if 'NormFactor: "bkgScale"' not in text:
    text = text.replace(
        'NormFactor: "topWidth"\n',
        'NormFactor: "bkgScale"\n'
        '  Title: "bkgScale"\n'
        '  Nominal: 1\n'
        '  Min: 0.5\n'
        '  Max: 1.5\n'
        '  Samples: Bkg_SR,Bkg_CR\n\n'
        'NormFactor: "topWidth"\n',
    )
target.write_text(text)
print(f"Wrote {target}")
PY
