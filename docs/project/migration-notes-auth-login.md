# Migration Note: Auth Login Payload

## Effective Date
- 2026-03-05

## Change Summary
`POST /api/v1/auth/login` accepts only:
- `identifier`
- `password`

The legacy request shape with `subject_id` and `role` is no longer supported.

## Client Action Required
1. Update all login requests to send `identifier` (login or e-mail) and `password`.
2. Remove any client logic that generates `subject_id + role` login payloads.
3. Verify error handling for invalid credentials and missing fields.

## Example
```json
{
  "identifier": "hr-user@example.com",
  "password": "StrongPassword!123"
}
```
