# AQG Studio - Security & Threat Model

## 1. Multi-Tenant Row Level Security (RLS) Architecture

AQG Studio enforces defense-in-depth across database, storage, authentication, and application tiers.

### 1.1 Database Tier (PostgreSQL RLS)
- Every user-owned table has `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` applied.
- All CRUD operations require `auth.uid() = user_id` (or `auth.uid() = id` for `profiles`).
- Cascading foreign keys (`ON DELETE CASCADE`) ensure child records (chunks, topics, questions, evaluations, exports) are cleanly purged when parent entities or profiles are deleted.

### 1.2 Storage Tier (Supabase Storage RLS)
- Buckets `source-documents` and `generated-exports` are strictly private (`public = false`).
- Storage RLS policy enforces that authenticated users can only read, insert, update, or delete objects where the first directory segment matches their own user ID:
  ```sql
  (storage.foldername(name))[1] = auth.uid()::text
  ```
- File uploads are validated for size limits (50MB) and allowed MIME types.

### 1.3 Application Tier (Repository Scoping)
- Every repository method in `backend/app/repositories/` takes a required `user_id: UUID` parameter.
- All SQL statements (`SELECT`, `UPDATE`, `DELETE`) compile with explicit `WHERE user_id = :user_id` clauses.
- Path traversal sequences (`..`, `\`, null bytes) and special characters are stripped in `backend/app/services/storage.py` before path resolution.

---

## 2. Authentication & JWT Verification (Phase 3)

### 2.1 Backend JWT Signature Verification
- The backend verifies JWT signatures via `python-jose` using `SUPABASE_JWT_SECRET` (HMAC-SHA256) rather than blindly decoding tokens.
- Strict claim validations:
  - **Expiration (`exp`)**: Tokens past expiry are rejected with `401 TOKEN_EXPIRED`.
  - **Audience (`aud`)**: Verifies audience contains `"authenticated"`.
  - **Subject (`sub`)**: Verifies `sub` is present and is a syntactically valid UUID string.
  - **Signature**: Tokens signed with untrusted keys are rejected with `401 TOKEN_INVALID`.
- The resolved identity is encapsulated in a frozen `CurrentUser` dependency:
  ```python
  @dataclass(frozen=True)
  class CurrentUser:
      user_id: uuid.UUID
      email: str | None
      role: str
      app_metadata: dict[str, Any]
      user_metadata: dict[str, Any]
      raw_claims: dict[str, Any]
  ```
- **Body `user_id` Tampering Protection**: The backend ignores any `user_id` provided in incoming JSON request bodies and overrides it with `CurrentUser.user_id`.

### 2.2 Next.js App Router Session Handling
- Session tokens are stored in `HttpOnly`, `SameSite=Lax`, `Secure` cookies managed via `@supabase/ssr`.
- Route protection is enforced in `middleware.ts` redirecting unauthenticated requests from `/dashboard` and protected application areas to `/auth/sign-in?returnUrl=...`.
- **Open Redirect Protection**: Return URLs are strictly validated to be relative paths (e.g. `/dashboard`), rejecting protocol-relative URLs (`//`) and external hostnames.

---

## 3. Secrets Management & Public/Private Boundaries

- **Zero Client-Side Secrets**:
  - The Next.js frontend only consumes `NEXT_PUBLIC_*` variables (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`).
  - The `SUPABASE_SERVICE_ROLE_KEY` is **never** provided to the frontend or checked into version control.
- **LLM API Keys**:
  - `OPENROUTER_API_KEY` and `NVIDIA_NIM_API_KEY` reside exclusively in the backend runtime environment.
- **Correlation ID Tracking**:
  - Incoming requests are assigned a unique `X-Correlation-ID` header.
  - Logs and API error responses correlate without exposing internal database stack traces or confidential prompt parameters to the client.

---

## 4. Threat Model & Mitigations

| Threat | Impact | Mitigation |
| :--- | :--- | :--- |
| **Forged / Tampered JWT** | Unauthorized user impersonation | Backend strictly verifies HMAC-SHA256 signature against `SUPABASE_JWT_SECRET` |
| **Open Redirect via returnUrl** | Phishing attack redirecting users after login | Frontend sanitizes `returnUrl` to ensure leading `/` and bans `//` protocol-relative paths |
| **Request Body User ID Spoofing** | Attacker creating resources under victim account | Repository methods unconditionally force `CurrentUser.user_id` from verified token |
| **Cross-Tenant Document Access** | Unauthorized reading of proprietary educational content | Storage RLS + Database table RLS + Repository user-scoping on all backend queries |
| **Path Traversal File Overwrite** | Malicious upload overwriting system files | `sanitize_filename` strips `..` and special characters; path generated deterministically as `{user_id}/{doc_id}/{filename}` |
| **LLM Token Exhaustion / DoS** | Free-tier token exhaustion across users | Per-user rate-limiting and daily quota tracking in `llm_usage_daily` table |
