# Phase 1 - Storage Adapter

Add config for:
- bucket
- endpoint
- credentials
- public URL base
- prefix
- presign TTL

Implementation rules:
- local filesystem remains the working directory for pipeline tools
- DB stores normalized storage keys, not absolute paths
- object storage upload/download is opt-in through `STORAGE_BACKEND`
