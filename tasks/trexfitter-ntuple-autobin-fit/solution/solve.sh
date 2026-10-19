#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

source = Path("/app/FitExampleNtuple.config")
target = Path("/tmp/FitExampleNtuple.local.config")
text = source.read_text()
text = text.replace(
    'NtuplePaths: "root://eosuser.cern.ch//eos/project/t/trexfitter-docs/test_inputs/Ntuple"',
    'NtuplePaths: "/trexinputs/eos/project/t/trexfitter-docs/test_inputs/Ntuple"',
)
text = text.replace("  LoggingFormat: NONE\n", "")
if "FitBlind: FALSE" not in text:
    text = text.replace(
        '  UseMinos: "mu_XS_ttH","tt_norm"\n',
        '  UseMinos: "mu_XS_ttH","tt_norm"\n  FitBlind: FALSE\n',
    )
if "DataType: DATA" not in text:
    text = text.replace('  Label: "5j >=3b"\n', '  Label: "5j >=3b"\n  DataType: DATA\n')
if "DataType: ASIMOV" not in text:
    text = text.replace('  Label: ">=6j >=3b"\n', '  Label: ">=6j >=3b"\n  DataType: ASIMOV\n')
target.write_text(text)
print(f"Wrote {target}")
PY
