# Phase 2 - Download + Materialize

Backend requirements:
- upload files to object storage after they are created
- download remote objects back into local cache when render/editor code needs a real local path
- redirect download endpoints to object URLs in production mode

Why:
- FFmpeg and subtitle rendering still need local file paths
- production users should not stream large binaries through FastAPI unless needed
