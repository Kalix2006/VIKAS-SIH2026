# VIKAS JWT Secret Rotation Runbook

This document defines the operational procedures for rotating JWT signing secrets in VIKAS without causing unexpected service disruptions or abrupt session termination for active users.

---

## 1. Authentication Architecture Overview

VIKAS uses a dual-token authentication model:
- **Access Tokens**: Short-lived JWTs (default: 30 minutes) signed with HMAC-SHA256 (`HS256`) using `JWT_SECRET`. They encapsulate `sub` (User ID), `role`, `district_id`, and `institute_id` for zero-lookup authorization and RLS context injection.
- **Refresh Tokens**: Long-lived (default: 7 days) cryptographically random 64-byte hex strings. The raw token is delivered exclusively to the client, while its SHA-256 hash is persisted in the PostgreSQL `refresh_tokens` table. Refresh tokens support one-time-use token rotation.

---

## 2. Rotation Scenarios

### Scenario A: Scheduled Routine Rotation (Zero User Downtime)
Performed periodically (e.g., every 90 days) as security hygiene.

1. **Generate New Secret**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Deploy Dual-Verification Secret**:
   VIKAS supports a primary and fallback secret. Update the deployment environment:
   ```env
   JWT_SECRET="<new-32-byte-hex-secret>"
   JWT_SECRET_FALLBACK="<old-32-byte-hex-secret>"
   ```
3. **Rolling Service Restart**:
   - Restart backend instances (Render/Railway rolling deploy).
   - Newly minted access tokens are signed with `JWT_SECRET`.
   - Incoming requests carrying access tokens signed with `JWT_SECRET_FALLBACK` remain valid until expiration.
4. **Decommission Fallback Secret**:
   - Wait 35 minutes (access token TTL of 30 minutes + 5 minutes clock skew buffer).
   - All active access tokens are now guaranteed to have rotated to the new secret.
   - Remove `JWT_SECRET_FALLBACK` from environment variables and perform final restart.

### Scenario B: Emergency Secret Revocation (Compromise / Breach)
Performed immediately if `JWT_SECRET` has leaked or an unauthorized party is suspected of forging tokens.

1. **Generate New Secret Immediately**:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Immediate Secret Swap**:
   Set `JWT_SECRET="<new-secret>"` and do NOT set a fallback secret. Deploy immediately. All forged and existing access tokens will instantly fail signature verification (`HTTP 401 Unauthorized`).
3. **Invalidate Stored Refresh Sessions**:
   Execute the following SQL command against PostgreSQL/Supabase to revoke all active sessions:
   ```sql
   UPDATE refresh_tokens SET revoked = true WHERE revoked = false;
   ```
4. **Audit**:
   Review server access logs and `audit_logs` for any anomalous activity recorded during the potential breach window.
5. **Notify Users**:
   All active users will be redirected to `/login` to re-authenticate cleanly.

---

## 3. Verification Checklist
- [ ] New secret is at least 32 bytes (256 bits) of entropy.
- [ ] `/health` reports 200 OK after environment update.
- [ ] Active login succeeds: `POST /auth/login`.
- [ ] Token refresh succeeds: `POST /auth/refresh`.
- [ ] Protected endpoints (`/auth/me`, `/planner/map`, etc.) accept the new access tokens.

