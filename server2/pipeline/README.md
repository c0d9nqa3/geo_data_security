# Local server2 processing package

This package is the first local, testable vertical slice for server2. It separates application behavior from Windows-specific integrations:

- `geo_security/crypto.py`: AES-GCM encryption for watermark payloads.
- `geo_security/vector_watermark.py`: Shapefile attribute watermarking while preserving geometry.
- `geo_security/task_store.py`: SQLite-backed durable task/artifact/approval metadata.
- `geo_security/pipeline.py`: local end-to-end processing flow and audit events.
- `geo_security/readonly_output.py`: result-id based read-only output guard.
- `geo_security/platform/`: VeraCrypt, sandbox, Sysmon and Windows adapters.

Tasks, results and approval status are persisted in SQLite; large files remain in the configured workspace. VeraCrypt is optional at the application layer and is exercised separately on the deployment host.
