# Testing Strategy

## Goals
- Prevent regressions in critical business flows.
- Keep verification reproducible for humans and LLM agents.

## Test Levels
| Level | Purpose | Minimum Requirement |
| --- | --- | --- |
| Unit | Validate isolated logic | Required for changed critical logic |
| Integration | Validate boundaries and contracts | Required for API/data boundary changes |
| End-to-end | Validate user-critical path | Required for high-risk releases |

## Change-Based Verification Matrix
| Change Type | Required Checks |
| --- | --- |
| Bugfix | Repro + regression test + adjacent behavior check |
| New feature | Happy path + one negative path + contract validation |
| Refactor | Existing tests + focused non-regression checks |

## Evidence Format
- Command
- Result (pass/fail)
- Artifact link/path (if available)
