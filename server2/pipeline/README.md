# Local server2 processing package

This package is the first local, testable vertical slice for server2. It deliberately separates application behavior from Windows-specific integrations:

- `geo_security/crypto.py`: AES-GCM encryption for watermark payloads.
- `geo_security/vector_watermark.py`: Shapefile attribute watermarking while preserving geometry.
- `geo_security/workspace.py`: project-isolated workspace and hash tracking.
- `geo_security/pipeline.py`: local end-to-end processing flow and audit events.
- `geo_security/readonly_output.py`: result-id based read-only output guard.
- `geo_security/platform/`: later VeraCrypt, sandbox, Sysmon and Windows service adapters.

The current local slice uses a normal local workspace because VeraCrypt is not installed yet. It must not be described as encrypted-volume validation until the VeraCrypt adapter is exercised on a real mounted volume.
