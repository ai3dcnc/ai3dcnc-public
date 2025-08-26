Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$OPS   = "samples/ops_min.json"
$SCH   = "schemas/ops_json.schema.json"
$PROF  = "profiles/Vitap_K2.profile.json"
$OUT   = "exports"

python tools/ops_tools.py validate $OPS $SCH

python tools/ops_tools.py to-tcn $OPS $PROF "$OUT/ops_min.tcn"
python tools/ops_tools.py to-csv $OPS "$OUT/ops_min.csv"

python tools/ops_tools.py from-tcn "$OUT/ops_min.tcn" $OPS "$OUT/ops_from_tcn.json"
python tools/ops_tools.py validate "$OUT/ops_from_tcn.json" $SCH
python tools/ops_tools.py to-tcn "$OUT/ops_from_tcn.json" $PROF "$OUT/ops_rerun.tcn"

if ((Get-FileHash "$OUT/ops_min.tcn").Hash -ne (Get-FileHash "$OUT/ops_rerun.tcn").Hash) { throw "TCN not deterministic" }

Write-Host "E2E OK"
exit 0
