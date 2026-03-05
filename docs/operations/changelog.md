# Changelog

## 2026-03-05
### Released
- `ADMIN-02` merged to `main` (PR #51): admin staff management (`GET/PATCH /api/v1/admin/staff*`) with strict guard reason-codes and `/admin/staff` UI.
- Backend package boundary refactor: admin governance extracted to dedicated `hrm_backend/admin` package.

### Breaking Changes
- Auth login payload is now strictly `identifier + password`.
- Legacy login payload `subject_id + role` is removed.

### Internal Cleanup
- Removed deprecated settings compatibility shims:
  - `hrm_backend.auth.utils.settings`
  - `hrm_backend.core.config.settings`
- Canonical settings entrypoint remains `hrm_backend.settings`.

### Next Up
- `ADMIN-03` opened as separate tracking task: issue #52.
