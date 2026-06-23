# Phase 4 - Auth And CORS

## Goal

Remove the assumption that frontend and API always share one origin.

## Work

- support multiple allowed frontend origins
- make cookie `SameSite` configurable
- make cookie `domain` configurable
- document the recommended same-site custom-domain setup

## Done

- Netlify + Northflank works with explicit cookie/CORS settings
- docs warn about the tradeoff between same-site subdomains and cross-site cookies
