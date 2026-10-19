#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

source = Path("/app/FitExampleUnfolding.config")
target = Path("/tmp/FitExampleUnfolding.local.config")
text = source.read_text()
old_path = "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Unfolding"
new_path = "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Unfolding"
text = text.replace(old_path, new_path)
text = text.replace("  LoggingFormat: NONE\n", "")
if "NumberOfRecoBins:" not in text:
    text = text.replace('  ShortLabel: "SR1"\n', '  ShortLabel: "SR1"\n  NumberOfRecoBins: 11\n')
if "PruningType: COMBINEDSIGNAL" not in text:
    text = text.replace("  SystDataPlots: TRUE\n", "  SystDataPlots: TRUE\n  PruningType: COMBINEDSIGNAL\n")
if "UnfoldNormXSec:" not in text:
    text = text.replace(
        "  UnfoldingResultMax: 100\n",
        "  UnfoldingResultMax: 100\n  UnfoldNormXSec: TRUE\n  UnfoldNormXSecBinN: 2\n",
    )
target.write_text(text)
print(f"Wrote {target}")
PY
