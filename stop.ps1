$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
New-Item -ItemType File -Force backend/.state/bridge-stop | Out-Null
docker compose --profile vision stop
