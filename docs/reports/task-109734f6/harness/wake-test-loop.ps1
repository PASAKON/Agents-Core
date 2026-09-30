param([string] $Log)
# The tab body for the wake spike: Read-Host each line, append it with a timestamp.
Add-Content -LiteralPath $Log -Value ("{0} READY pid={1} session={2}" -f (Get-Date -Format 'HH:mm:ss.fff'), $PID, (Get-Process -Id $PID).SessionId)
while ($true) {
    $l = Read-Host 'wake'
    Add-Content -LiteralPath $Log -Value ("{0} RECV [{1}]" -f (Get-Date -Format 'HH:mm:ss.fff'), $l)
    if ($l -eq 'quit') { exit 0 }
}
