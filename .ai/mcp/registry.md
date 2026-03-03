# MCP Registry

Track MCP servers used by this project.

| Name | Purpose | Access | Owner | Notes |
| --- | --- | --- | --- | --- |
| github | Pull requests, issues, checks | read/write | platform | restrict to repo scope |
| docs | Internal documentation search | read-only | platform | no secret data writes |
| postgres | Operational queries | read-only by default | data | write access only for approved migrations |

## Onboarding Checklist
- Define least-privilege scopes.
- Document authentication method.
- Add failure and timeout behavior.
- Add audit trail location.
