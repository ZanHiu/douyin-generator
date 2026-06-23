# Phase 3 - API And Worker On Northflank

## Goal

Reuse the existing backend container for managed API and worker services.

## Work

- document API service start command
- document worker service start command
- keep health endpoints explicit
- keep DB/Redis wait logic usable with external managed services

## Done

- one backend image can serve both Northflank services
- service-specific commands are explicit and repeatable
