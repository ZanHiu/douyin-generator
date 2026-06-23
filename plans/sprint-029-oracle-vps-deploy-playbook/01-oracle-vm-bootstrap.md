# Phase 1 - Oracle VM Bootstrap

Objective:

- choose a practical Oracle VM baseline
- bootstrap the host with Docker, Compose plugin, Git, and basic firewall support

Deliverables:

- `deploy/oracle/bootstrap-ubuntu.sh`
- Oracle-specific host prep steps in docs

Notes:

- prefer Ubuntu x86_64 first for the lowest dependency risk
- free-tier shape changes by region and account availability, so docs should describe the decision rather than hardcode a single shape
