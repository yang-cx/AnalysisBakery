#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

source = Path("/app/FitExampleTemplate_1D.config")
target = Path("/tmp/FitExampleTemplate_1D.local.config")
text = source.read_text()
text = text.replace(
    'HistoPath: "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Template"',
    'HistoPath: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Template"',
)
text = text.replace("  LoggingFormat: NONE\n", "")
text = text.replace("FitFunction: LINEAR", "FitFunction: QUADRATIC")
if "ParamLimits: Signal_1p0_172p5@SR_emu@0:0:-10:10" not in text:
    text = text.replace(
        "  FitFunction: QUADRATIC\n",
        "  FitFunction: QUADRATIC\n"
        "  ParamLimits: Signal_1p0_172p5@SR_emu@0:0:-10:10\n"
        "  ParamStartValue: Signal_1p0_172p5@SR_emu@0:0:1\n",
    )
target.write_text(text)
print(f"Wrote {target}")
PY
