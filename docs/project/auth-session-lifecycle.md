# Authentication and Session Lifecycle (TASK-01-02)

## Last Updated
- Date: 2026-03-04
- Updated by: backend-engineer

This document defines the Phase-1 authentication baseline for backend APIs.
Source of truth: `apps/backend/src/hrm_backend/auth.py` and `apps/backend/src/hrm_backend/api/auth.py`.

## Token Model

| Token | Purpose | TTL | Storage | Rotation |
| --- | --- | --- | --- | --- |
| Access token (`Bearer`) | Authorize API requests | `HRM_ACCESS_TOKEN_TTL_SECONDS` (default: 900s) | Client-side (short-lived) | Re-issued on login/refresh |
| Refresh token | Renew access token and extend session | `HRM_REFRESH_TOKEN_TTL_SECONDS` (default: 604800s) | Client-side (secure storage) + server-side hash | Mandatory rotation on every refresh |

## Session Model
- Session id (`sid`) is created at login.
- Server keeps in-memory session record with subject, role, refresh token hash, expiry, and revoke marker.
- Logout revokes session immediately.
- Access token is valid only when:
  - signature is valid,
  - token not expired,
  - linked session exists,
  - session is not revoked,
  - session claims (subject/role) match token claims.

## API Endpoints

| Endpoint | Method | Purpose | Auth Required |
| --- | --- | --- | --- |
| `/api/v1/auth/login` | `POST` | Issue access + refresh token pair | no |
| `/api/v1/auth/refresh` | `POST` | Rotate refresh token and issue new access token | refresh token in body |
| `/api/v1/auth/logout` | `POST` | Revoke current session | access token |
| `/api/v1/auth/me` | `GET` | Return current identity claims | access token |

## Configuration
- `HRM_AUTH_SECRET`: HMAC signing secret for access token signature.
- `HRM_ACCESS_TOKEN_TTL_SECONDS`: access token TTL.
- `HRM_REFRESH_TOKEN_TTL_SECONDS`: refresh token/session TTL.

## Security Baseline and Current Limits
- Refresh token is never stored in plaintext server-side (hash only).
- Session revocation is immediate for API checks.
- Current storage is process-local in memory (non-persistent).
- Horizontal scaling requires shared persistent session storage (planned after MVP baseline).

## RBAC Integration
- RBAC role is no longer taken from `X-Role` header for protected routes.
- RBAC role is resolved from validated token claims (`role`) after access token/session checks.

## Next Steps
- `TASK-01-03`: move access policy enforcement to middleware for API and background jobs.
- `TASK-01-04`: add immutable audit logs for auth/session and sensitive data access.
- `TASK-01-05`: map auth/session controls to Belarus/Russia legal controls matrix.
