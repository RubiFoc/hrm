# Changelog

## 2026-03-05
### Breaking Changes
- Auth login payload is now strictly `identifier + password`.
- Legacy login payload `subject_id + role` is removed.

### Internal Cleanup
- Removed deprecated settings compatibility shims:
  - `hrm_backend.auth.utils.settings`
  - `hrm_backend.core.config.settings`
- Canonical settings entrypoint remains `hrm_backend.settings`.
