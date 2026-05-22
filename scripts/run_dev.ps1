$ErrorActionPreference = "Stop"

$envHost = if ($env:PMOS_API_HOST) { $env:PMOS_API_HOST } else { "127.0.0.1" }
$envPort = if ($env:PMOS_API_PORT) { $env:PMOS_API_PORT } else { "8000" }

uvicorn pmos.api.app:app --reload --host $envHost --port $envPort
