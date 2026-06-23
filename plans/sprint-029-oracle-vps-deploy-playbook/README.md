# Sprint 029 - Oracle VPS Deploy Playbook

Goal: turn the current private-production bootstrap into a concrete Oracle Cloud VPS deployment path with minimal operator guesswork.

Scope:

- document Oracle VM provisioning choices
- add a server bootstrap script for Ubuntu
- add a reverse proxy example for domain + HTTPS
- refine production compose config so frontend can bind to localhost when a reverse proxy is used
- keep the app architecture unchanged

Out of scope:

- Terraform or IaC
- managed Kubernetes or ECS migration
- automated DNS provisioning
- high-availability or autoscaling

Expected outcome:

- one Oracle Ubuntu VM can run the current stack
- operator can choose either direct `:8080` access or domain + Caddy
- production env setup is explicit and repeatable
