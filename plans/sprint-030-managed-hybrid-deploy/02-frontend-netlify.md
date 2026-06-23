# Phase 2 - Frontend On Netlify

## Goal

Make the Vue app deployable on Netlify without assuming same-origin `/api`.

## Work

- add `netlify.toml`
- pin pnpm for platform builds
- add `VITE_API_BASE_URL`
- keep SPA fallback routing
- resolve relative job/edit download links against the configured API base URL

## Done

- Netlify can build the frontend from repo root
- frontend runtime requests can target an external API domain
