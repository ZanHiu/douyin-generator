# Sprint 030 - Managed Hybrid Deploy

Goal: add a concrete deploy path for the low-cost managed stack:

- frontend on `Netlify`
- API + worker on `Northflank`
- PostgreSQL on `Supabase`
- Redis on `Upstash`
- object storage on `Cloudflare R2`

Scope:

- add deploy artifacts for Netlify and Northflank
- make frontend API/download URLs work when frontend and API live on different domains
- make auth cookie and CORS settings configurable for cross-origin or same-site subdomain deploys
- add managed env examples and step-by-step docs

Out of scope:

- Terraform
- full AWS migration
- local-to-cloud automated sync scripts
- CI/CD hardening beyond platform-native deploys

Expected outcome:

- the app can be deployed without Docker Compose using managed services
- Netlify frontend can talk to Northflank API correctly
- operator can choose either same-site custom domains or a looser cross-site cookie setup
