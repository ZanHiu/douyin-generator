# Sprint 027 - Production Storage Backend

Goal: turn the storage abstraction into a production-ready backend that can keep local dev on filesystem while supporting S3-compatible object storage for deploys.

Scope:
- add object-storage config and adapter behavior
- keep local files as working cache for FFmpeg/editor flows
- upload artifacts/manifests to object storage automatically
- support redirect-style downloads for remote objects
- keep local backend unchanged for current development flow

Done when:
- `STORAGE_BACKEND=local` works exactly as before
- `STORAGE_BACKEND=s3|minio|r2` can upload artifacts and resolve them back locally
- download endpoints can return remote object URLs when object storage is enabled
- touched backend tests pass
