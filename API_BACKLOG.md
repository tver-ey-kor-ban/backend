# API Backlog — Backend Improvement Items

Priority: **P0** = blocking / causes bugs · **P1** = high value · **P2** = nice-to-have

---

## P0 — Blocking / Causes Frontend Bugs

### [P0-1] `GET /auth/me/roles` must reflect shop membership roles

**Problem:** The endpoint always returns `roles: ["user"]` regardless of whether the user is a shop owner or mechanic. Ownership lives in `UserShop` records, not in the `users.roles` field. This caused the login bug where shop owners were blocked from the dashboard because `roles.includes('owner')` was always `false`.

**Current response:**
```json
{ "username": "owner1", "roles": ["user"], "is_superuser": false }
```

**Expected response:**
```json
{ "username": "owner1", "roles": ["user", "owner"], "is_superuser": false, "shop_roles": [{ "shop_id": 1, "role": "owner" }] }
```

**Recommended fix:** Augment the response to include a `shop_roles` array derived from `UserShop` records. The frontend can then derive `isOwner` / `isMechanic` from this field without a separate `GET /shops/my-shops` call.

---

### [P0-2] Appointment `rejected` status missing from admin filter

**Problem:** `POST /mechanic/shops/{id}/bookings/{id}/action` with `action: "reject"` transitions the appointment to status `rejected`. But `GET /admin/appointments?status=rejected` returns nothing because the filter's allowed values only include `pending · confirmed · completed · cancelled`. Rejected appointments are invisible to admins.

**Fix:** Add `rejected` to the `status` query param enum for `GET /admin/appointments`.

---

### [P0-3] Admin statistics response shape mismatch

**Problem:** `GET /admin/statistics` returns a flat summary object (`total_users`, `total_shops`, etc.) per the frontend integration, but RBAC.md documents a nested structure with sub-objects (`users.total`, `shops.active`, `revenue.total`, etc.). One of these is wrong.

**Fix:** Align the actual response, the RBAC.md documentation, and the frontend `AdminStats` type to a single agreed shape. If the nested structure is correct on the backend, update `AdminStats` in `core/types/index.ts`; if the flat shape is correct, update RBAC.md.

---

## P1 — High Value

### [P1-1] Shop owner has no full-list endpoint for appointments

**Problem:** `GET /mechanic/shops/{id}/pending-bookings` only returns `pending` status. Shop owners cannot see confirmed, completed, or cancelled appointments without going through the admin endpoint (which they can't access).

**Fix:** The endpoint `GET /customers/shops/{shop_id}/appointments?status=...` already exists in the API docs (`🔧` auth) and is referenced in RBAC.md but was missing from earlier documentation. Verify it is implemented and returns the correct shape. The frontend `BookingsPage` should be updated to use it after confirmation.

---

### [P1-2] Silent token expiry — no refresh endpoint integration

**Problem:** Access tokens expire after 30 minutes. The backend provides `POST /auth/refresh` but the frontend never calls it. After 30 minutes, the next API call returns `401`, the interceptor clears auth state, and the user is logged out mid-session without warning.

**Fix (backend):** No backend change needed; the endpoint exists.

**Fix (frontend):** In `apiClient.ts`, add a response interceptor that catches `401`, checks for a stored refresh token, calls `POST /auth/refresh`, stores the new access token, and retries the original request. Only dispatch `auth:unauthorized` if refresh also fails.

**Recommended backend improvement:** Implement refresh token rotation — issue a new refresh token on each `/auth/refresh` call and revoke the old one. The current behaviour (refresh token is not rotated) means a stolen refresh token is valid for 7 days with no way to invalidate it.

---

### [P1-3] No shop-level statistics endpoint for owners

**Problem:** Admin has `GET /admin/statistics` for platform-wide totals. Shop owners have no equivalent — they cannot see their own shop's revenue, booking count, or order count from a single endpoint. They must piece it together from individual list endpoints.

**Proposed endpoint:**
```
GET /shops/{shop_id}/statistics   🔒 🔧
```
```json
{
  "shop_id": 1,
  "appointments": { "total": 45, "pending": 3, "confirmed": 5, "completed": 35, "cancelled": 2, "rejected": 0 },
  "orders": { "total": 30, "pending": 2, "confirmed": 4, "processing": 1, "ready": 0, "completed": 22, "cancelled": 1 },
  "revenue": { "appointments": 1800.00, "orders": 450.50, "total": 2250.50 },
  "products": 24,
  "services": 8
}
```
This would power a meaningful owner dashboard instead of just showing the pending counts.

---

### [P1-4] Order rejection produces unknown status

**Problem:** `POST /mechanic/shops/{id}/orders/{id}/action` with `action: "reject"` is documented, but the resulting order status is never specified. The admin's order status filter lists `cancelled` but not `rejected`. It is unclear whether rejected orders become `rejected` or `cancelled`.

**Fix:** Document the status transition explicitly. If `reject` → `cancelled`, remove the `reject` action and expose a `cancel` action. If `reject` → `rejected`, add `rejected` to all status filter enums (same issue as P0-2).

---

### [P1-5] Pagination missing from mechanic-facing endpoints

**Problem:** `GET /mechanic/shops/{id}/pending-bookings` and `GET /mechanic/shops/{id}/pending-orders` have no `skip`/`limit` or `page`/`page_size` params. A busy shop with hundreds of pending items will return all of them in one response with no way to page through them.

**Fix:** Add standard pagination params (`page=1`, `limit=50`, max `200`) to both endpoints. Include `total` in the response.

---

### [P1-6] No endpoint to activate / deactivate a shop (admin)

**Problem:** Admin can only hard-delete a shop (`DELETE /admin/shops/{id}`). There is no soft toggle (`is_active = false`) for admins. Shop owners can soft-delete their own shop, but an admin who wants to temporarily suspend a shop without destroying it has no option.

**Proposed endpoint:**
```
PUT /admin/shops/{shop_id}/status
Body: { "is_active": false }
```

---

### [P1-7] `GET /shops/my-shops` should be a required session endpoint

**Problem:** Every frontend session calls `GET /shops/my-shops` on login for any authenticated user (customers included) to determine role. For customers this is a wasted call that always returns `[]`.

**Fix (backend):** No change needed if performance is acceptable.

**Longer-term option:** Include a `shop_memberships` array in the `GET /auth/me` response (already present on `GET /admin/users/{id}/` for admins). This eliminates the extra round-trip for all users.

---

### [P1-8] Chat endpoints are undocumented in RBAC.md and unimplemented in frontend

**Problem:** `POST /chat/rooms`, `GET /chat/rooms`, `POST /chat/rooms/{id}/messages` etc. exist in `API_DOCUMENTATION.md` with full schemas, but:
- The frontend has no Chat page or component
- The RBAC.md previously had no endpoint reference section for Chat
- It is unclear who can initiate a chat (any authenticated user, or only shop members?)

**Fix (backend):** Confirm the intended access control for chat creation. If any authenticated user can create a room, document this clearly. Consider adding `GET /chat/rooms/unread-count` as a summary endpoint so the header notification badge can show a total count without fetching all rooms.

**Fix (frontend):** Build a Chat page at `/owner/chat` with room list and message thread view.

---

## P2 — Nice to Have

### [P2-1] Image search endpoint is a placeholder

`POST /shops/{shop_id}/products/search-by-image` is documented as a placeholder that returns products with images attached rather than performing visual similarity search. Either implement ML-based visual search or remove the endpoint until it is ready. The frontend should hide any UI for this feature in the meantime.

---

### [P2-2] No bulk actions on orders or bookings

Shop owners must accept/reject orders and bookings one at a time. For busy shops this is tedious.

**Proposed endpoints:**
```
POST /mechanic/shops/{shop_id}/bookings/bulk-action
Body: { "appointment_ids": [1, 2, 3], "action": "accept" }

POST /mechanic/shops/{shop_id}/orders/bulk-action
Body: { "order_ids": [1, 2, 3], "action": "accept" }
```

---

### [P2-3] `GET /admin/statistics/daily` response is missing totals context

**Current response:** Returns `new_users`, `new_shops`, `new_appointments`, `new_orders` for the period but no revenue breakdown. The admin dashboard cannot show daily revenue trends.

**Add to response:**
```json
{
  "period_days": 30,
  "start_date": "...",
  "end_date": "...",
  "new_users": 18,
  "new_shops": 2,
  "new_appointments": 42,
  "new_orders": 15,
  "revenue": { "appointments": 1200.00, "orders": 320.50, "total": 1520.50 }
}
```

---

### [P2-4] No real-time notifications (WebSocket / SSE)

Notifications currently require the user to manually refresh or poll `GET /mechanic/my-notifications`. The frontend has no polling logic.

**Fix:** Implement WebSocket (`ws://`) or Server-Sent Events (`GET /me/events`) for push notifications. At minimum, add a `?poll=true` query param that long-polls and returns immediately when a new notification arrives.

---

### [P2-5] Search on `/admin/shops` is missing

`GET /admin/shops` accepts `skip`, `limit`, `is_active` but has no `search` param. Admin cannot search shops by name. Compare with `/admin/users` which supports `search`.

**Fix:** Add `search` query param that filters by `name` (case-insensitive ILIKE).

---

### [P2-6] No way to filter quotations by appointment

`GET /quotations/shops/{shop_id}?status=draft` filters by status only. When viewing a specific appointment, there is no way to fetch only the quotations linked to that appointment.

**Fix:** Add `appointment_id` as an optional query param.

---

### [P2-7] `DELETE /shops/{shop_id}/members/{user_id}` is a soft deactivate, not a true remove

The endpoint sets `is_active = false` on the `UserShop` record but does not remove it. There is no way to fully remove a member or re-activate a previously deactivated member.

**Fix:** Add:
```
PUT /shops/{shop_id}/members/{user_id}/status   Body: { "is_active": true/false }
DELETE /shops/{shop_id}/members/{user_id}        (hard remove, current "delete" becomes this)
```

---

### [P2-8] No endpoint to resend a quotation or invoice

Once a quotation/invoice is `sent`, there is no endpoint to re-send it to the customer (e.g., if their email changed or the first send failed).

**Fix:** Add:
```
POST /quotations/shops/{shop_id}/{quotation_id}/resend
POST /invoices/shops/{shop_id}/{invoice_id}/resend
```

---

## Response Shape Standardisation

Several endpoints use inconsistent envelope shapes. Standardise all paginated list responses to:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

Affected endpoints currently using non-standard shapes:
- `GET /mechanic/shops/{id}/pending-bookings` → `{ count, bookings }` (should be `{ total, items }`)
- `GET /admin/users` → `{ total, skip, limit, users }` (should be `{ total, page, limit, items }`)
- `GET /admin/appointments` — shape not fully documented

Consistent envelopes allow the frontend to use a single `PaginatedResponse<T>` generic type rather than per-endpoint interface adapters.
