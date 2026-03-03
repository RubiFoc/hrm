# MCP Access Policy

## Principles
- Use least privilege by default.
- Separate read-only and write-capable identities.
- Store credentials in secret manager, never in repository.
- Require explicit approval for destructive operations.

## Required Controls
- Scope every server token to exact project resources.
- Rotate credentials on a fixed schedule.
- Log all write operations with request IDs.
- Define rollback playbooks for each write-capable server.

## Review Cadence
- Monthly: verify active integrations and permissions.
- Quarterly: access recertification by service owner.
