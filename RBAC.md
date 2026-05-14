# RBAC — Role-Based Access Control

## Overview

The system has four roles. This document covers the two most privileged: **Admin** and **Shop Owner**. A user can be both an admin on the platform and an owner of one or more shops simultaneously.

| Role | How it is granted | Token requirement |
|------|------------------|-------------------|
| **Admin** | `is_superuser = true` on the `users` row | Valid JWT + `is_superuser` claim |
| **Shop Owner** | `UserShop.role = "owner"` for a specific shop | Valid JWT + owner membership record |
| Mechanic | `UserShop.role = "mechanic"` for a specific shop | Valid JWT + mechanic membership record |
| Customer | Any authenticated user | Valid JWT |
| Public | — | No token needed |

**Auth header for all protected endpoints:**
```
Authorization: Bearer <access_token>
```

---

## Admin Role

### Access requirement

```
is_superuser = true  (set on the User record)
```

Admins bypass all shop-level permission checks. Their scope is the **entire platform**, not individual shops.

### Safety restrictions built into the code

| Action | Restriction |
|--------|-------------|
| Deactivate user | Cannot deactivate own account |
| Revoke admin | Cannot remove own `is_superuser` flag |
| Delete user | Cannot delete own account |

---

### Endpoint Reference

#### User Management

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/admin/users` | `skip`, `limit` (max 1000), `search`, `is_active`, `is_superuser` | List all users, paginated |
| `GET` | `/api/v1/admin/users/{user_id}` | — | Full user detail + shop memberships |
| `PUT` | `/api/v1/admin/users/{user_id}/status` | `is_active` (bool) | Activate or deactivate account |
| `PUT` | `/api/v1/admin/users/{user_id}/role` | `is_superuser` (bool) | Grant or revoke admin privileges |
| `DELETE` | `/api/v1/admin/users/{user_id}` | — | Permanently delete user |

**GET /admin/users response:**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 100,
  "users": [
    {
      "id": 1,
      "username": "customer1",
      "email": "customer1@example.com",
      "full_name": "Test Customer",
      "is_active": true,
      "is_superuser": false,
      "roles": "user",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**GET /admin/users/{id} response:**
```json
{
  "id": 3,
  "username": "owner1",
  "email": "owner@example.com",
  "full_name": "Shop Owner",
  "is_active": true,
  "is_superuser": false,
  "roles": "user",
  "created_at": "2024-01-01T00:00:00",
  "shop_memberships": [
    { "shop_id": 1, "shop_name": "Test Garage", "role": "owner", "is_active": true }
  ]
}
```

---

#### Shop Management

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/admin/shops` | `skip`, `limit` (max 1000), `is_active` | List all shops |
| `GET` | `/api/v1/admin/shops/{shop_id}` | — | Shop detail + stats + member list |
| `DELETE` | `/api/v1/admin/shops/{shop_id}` | — | Permanently delete shop (hard delete) |

**GET /admin/shops/{id} response:**
```json
{
  "id": 1,
  "name": "Test Garage",
  "description": "...",
  "address": "123 Main St",
  "phone": "+1234567890",
  "email": "garage@test.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "statistics": {
    "products": 24,
    "services": 8,
    "appointments": 120,
    "orders": 45
  },
  "members": [
    { "user_id": 3, "username": "owner1", "role": "owner", "is_active": true },
    { "user_id": 4, "username": "mechanic1", "role": "mechanic", "is_active": true }
  ]
}
```

> **Note:** Admin delete is a **hard delete** (row removed from DB). Shop owner delete is a soft delete (`is_active = false`).

---

#### Platform Statistics

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/admin/statistics` | — | Platform-wide totals snapshot |
| `GET` | `/api/v1/admin/statistics/daily` | `days` (1–365, default 30) | Activity counts for last N days |

**GET /admin/statistics response:**
```json
{
  "users":  { "total": 150, "active": 140, "inactive": 10, "admins": 2 },
  "shops":  { "total": 12,  "active": 10,  "inactive": 2 },
  "catalog": { "products": 280, "services": 95 },
  "appointments": {
    "total": 380, "pending": 45, "completed": 300, "cancelled": 35
  },
  "orders": {
    "total": 210, "pending": 20, "completed": 180, "cancelled": 10
  },
  "revenue": {
    "appointments": 12450.00,
    "orders": 2790.50,
    "total": 15240.50
  }
}
```

**GET /admin/statistics/daily response:**
```json
{
  "period_days": 30,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-01-31T00:00:00",
  "new_users": 18,
  "new_shops": 2,
  "new_appointments": 42,
  "new_orders": 15
}
```

---

#### Bookings & Orders (read-only, all shops)

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/admin/appointments` | `skip`, `limit`, `status`, `shop_id` | All appointments across platform |
| `GET` | `/api/v1/admin/orders` | `skip`, `limit`, `status`, `shop_id` | All product orders across platform |

`status` values for appointments: `pending` · `confirmed` · `completed` · `cancelled`  
`status` values for orders: `pending` · `confirmed` · `processing` · `ready` · `completed` · `cancelled`

---

#### Ratings Moderation

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/admin/ratings` | `skip`, `limit` | All product + service ratings |
| `DELETE` | `/api/v1/admin/ratings/product/{rating_id}` | — | Remove a product review |
| `DELETE` | `/api/v1/admin/ratings/service/{rating_id}` | — | Remove a service review |

---

### Admin Capability Summary

| Domain | Read | Write | Delete |
|--------|------|-------|--------|
| Users | All users, full detail | Activate/deactivate, grant/revoke admin | Hard delete |
| Shops | All shops + stats | — | Hard delete |
| Appointments | All shops, all statuses | — | — |
| Orders | All shops, all statuses | — | — |
| Ratings | All product + service ratings | — | Hard delete |
| Statistics | Platform totals + daily breakdown | — | — |

---
---

## Shop Owner Role

### Access requirement

```
UserShop record exists where:
  user_id  = <current user>
  shop_id  = <shop in the URL path>
  role     = "owner"
  is_active = true
```

Ownership is **per-shop**. A user can be owner of Shop A and mechanic at Shop B at the same time.

### Safety restrictions

| Action | Restriction |
|--------|-------------|
| Add member | Shop ID in body must match URL path shop ID |
| Member role | Only `"owner"` or `"mechanic"` are valid |
| Delete shop | Soft delete only (`is_active = false`) |
| Booking action | Only `"accept"` or `"reject"` |
| Order action | Only `"accept"` or `"reject"` |

---

### Endpoint Reference

#### Shop

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/shops` | Create a new shop — creator becomes owner automatically |
| `GET` | `/api/v1/shops/my-shops` | List all shops where user is owner or mechanic |
| `PUT` | `/api/v1/shops/{shop_id}` | Update shop details |
| `DELETE` | `/api/v1/shops/{shop_id}` | Soft-delete shop (`is_active = false`) |

**POST /shops request:**
```json
{
  "name": "My Garage",
  "description": "Best garage in town",
  "address": "456 Main St",
  "phone": "+1234567890",
  "email": "shop@example.com"
}
```

**GET /shops/my-shops response:**
```json
[
  { "shop_id": 1, "shop_name": "Test Garage", "role": "owner",    "is_active": true },
  { "shop_id": 3, "shop_name": "Branch Shop", "role": "mechanic", "is_active": true }
]
```

---

#### Member Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/shops/{shop_id}/members` | Add a user to the shop (owner or mechanic) |
| `GET` | `/api/v1/shops/{shop_id}/members` | List all members (owners + mechanics) |
| `PUT` | `/api/v1/shops/{shop_id}/members/{user_id}/role` | Change a member's role |
| `DELETE` | `/api/v1/shops/{shop_id}/members/{user_id}` | Remove a member (soft deactivate) |

**POST /members request:**
```json
{ "user_id": 5, "shop_id": 1, "role": "mechanic" }
```
> `role` must be `"owner"` or `"mechanic"`. Mechanics can also view with `GET /members`.

**GET /members response:**
```json
[
  { "user_id": 3, "username": "owner1",    "full_name": "Shop Owner",    "role": "owner",    "is_active": true },
  { "user_id": 4, "username": "mechanic1", "full_name": "Test Mechanic", "role": "mechanic", "is_active": true }
]
```

---

#### Products

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/shops/{shop_id}/products` | Create product |
| `GET` | `/api/v1/shops/{shop_id}/products` | List all active products |
| `GET` | `/api/v1/shops/{shop_id}/products/{product_id}` | Get product detail |
| `PUT` | `/api/v1/shops/{shop_id}/products/{product_id}` | Update product |
| `DELETE` | `/api/v1/shops/{shop_id}/products/{product_id}` | Soft-delete product |
| `GET` | `/api/v1/shops/{shop_id}/products/search` | Search products (owner/mechanic) |
| `GET` | `/api/v1/shops/{shop_id}/products/by-service/{service_id}` | Recommended products for a service |
| `POST` | `/api/v1/shops/{shop_id}/products/search-by-image` | Image search (placeholder) |

**POST/PUT /products request:**
```json
{
  "name": "Synthetic Oil 5W-30",
  "description": "Full synthetic motor oil",
  "price": 29.99,
  "cost": 18.00,
  "stock_quantity": 50,
  "sku": "OIL-5W30",
  "category_id": 1
}
```

> `GET /products/search` accepts `?q=`, `?category_id=`, `?min_price=`, `?max_price=` and requires owner or mechanic auth. This is a **management** endpoint — use `GET /customers/shops/{id}/browse/products?search=` for public customer-facing search.

---

#### Services

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/shops/{shop_id}/services` | Create service |
| `GET` | `/api/v1/shops/{shop_id}/services` | List all active services |
| `GET` | `/api/v1/shops/{shop_id}/services/{service_id}` | Get service detail |
| `PUT` | `/api/v1/shops/{shop_id}/services/{service_id}` | Update service |
| `DELETE` | `/api/v1/shops/{shop_id}/services/{service_id}` | Soft-delete service |
| `GET` | `/api/v1/shops/{shop_id}/services/by-type` | List services grouped by type |

**POST/PUT /services request:**
```json
{
  "name": "Oil Change",
  "description": "Full oil change with filter",
  "price": 39.99,
  "duration_minutes": 30,
  "service_type": "shop_based",
  "mobile_service_area": null,
  "mobile_service_fee": 0
}
```

| `service_type` | Meaning |
|----------------|---------|
| `shop_based` | Customer brings vehicle to the shop |
| `mobile` | Mechanic travels to customer location |
| `pickup_drop` | Shop picks up vehicle, services it, returns it |

---

#### Categories

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/categories` | Create category |
| `PUT` | `/api/v1/categories/{category_id}` | Update category |
| `DELETE` | `/api/v1/categories/{category_id}` | Delete category |
| `POST` | `/api/v1/categories/service-links` | Link a category to a service |

> Read endpoints (`GET /categories`, `GET /categories/tree`, etc.) are **public** — no auth required.

---

#### Booking Management

Owner can do everything a mechanic can do plus view individual mechanic performance.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/mechanic/shops/{shop_id}/pending-bookings` | All pending appointments |
| `GET` | `/api/v1/mechanic/shops/{shop_id}/bookings/{appointment_id}` | Appointment detail |
| `POST` | `/api/v1/mechanic/shops/{shop_id}/bookings/{appointment_id}/action` | Accept or reject |
| `GET` | `/api/v1/mechanic/shops/{shop_id}/today-bookings` | Today's appointments |

**Accept / Reject request:**
```json
{ "action": "accept", "notes": "We'll start at 10 AM" }
```
```json
{ "action": "reject", "reason": "Fully booked that day" }
```

Status transitions:
- `accept` → `confirmed` (customer receives notification)
- `reject` → `rejected` (customer receives notification)

---

#### Order Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/mechanic/shops/{shop_id}/pending-orders` | Pending product orders |
| `POST` | `/api/v1/mechanic/shops/{shop_id}/orders/{order_id}/action` | Accept or reject order |
| `PUT` | `/api/v1/mechanic/shops/{shop_id}/orders/{order_id}/ready` | Mark order ready for pickup |

**Accept / Reject request:**
```json
{ "action": "accept" }
```
```json
{ "action": "reject", "reason": "Out of stock" }
```

---

#### Mechanic Performance Analytics

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| `GET` | `/api/v1/shops/{shop_id}/mechanics/performance` | `date_from`, `date_to` (YYYY-MM-DD) | All mechanics comparison (default: last 30 days) |
| `GET` | `/api/v1/shops/{shop_id}/mechanics/performance/top` | `metric` (`revenue`/`rating`/`jobs`), `limit` (1–20) | Top N mechanics by metric |
| `GET` | `/api/v1/shops/{shop_id}/mechanics/{mechanic_id}/performance` | `date_from`, `date_to` | Individual mechanic summary + recent jobs |
| `GET` | `/api/v1/shops/{shop_id}/mechanics/{mechanic_id}/performance/history` | `page`, `page_size` (max 100) | Full paginated job history |
| `POST` | `/api/v1/shops/{shop_id}/mechanics/{mechanic_id}/performance/record` | — | Record a completed job |

**GET /mechanics/performance response shape:**
```json
{
  "shop_summary": {
    "total_jobs": 45,
    "total_revenue": 2250.00,
    "mechanic_count": 3
  },
  "mechanics": [
    {
      "mechanic_id": 4,
      "username": "mechanic1",
      "total_jobs": 20,
      "total_revenue": 980.00,
      "average_rating": 4.6
    }
  ],
  "total_mechanics": 3
}
```

**POST /performance/record request:**
```json
{
  "appointment_id": 12,
  "service_name": "Oil Change",
  "revenue_generated": 39.99,
  "estimated_duration": 30,
  "actual_duration": 25
}
```

---

#### Quotations

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/quotations/shops/{shop_id}` | Create quotation for an appointment |
| `GET` | `/api/v1/quotations/shops/{shop_id}` | List shop quotations (filter by `status`) |
| `GET` | `/api/v1/quotations/shops/{shop_id}/{quotation_id}` | Quotation detail |
| `PUT` | `/api/v1/quotations/shops/{shop_id}/{quotation_id}` | Update draft quotation |
| `POST` | `/api/v1/quotations/shops/{shop_id}/{quotation_id}/send` | Send quotation to customer |

`status` filter values: `draft` · `sent` · `approved` · `rejected` · `expired`

**POST /quotations request:**
```json
{
  "appointment_id": 1,
  "title": "Engine Repair Estimate",
  "description": "Full diagnostics and repair",
  "items": [
    { "item_type": "labor", "name": "Engine Diagnostics", "quantity": 1, "unit_price": 75 },
    { "item_type": "part",  "name": "Spark Plugs",        "quantity": 4, "unit_price": 12.5 }
  ],
  "labor_cost": 75,
  "parts_cost": 50,
  "tax_amount": 10,
  "discount_amount": 5
}
```

---

#### Repair Progress

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/repair-progress/shops/{shop_id}` | Start a repair progress record |
| `PUT` | `/api/v1/repair-progress/shops/{shop_id}/{progress_id}` | Advance to next stage |
| `GET` | `/api/v1/repair-progress/shops/{shop_id}` | List all repairs (filter by `stage`) |

**Repair stages in order:**

```
received → diagnosing → waiting_parts → in_progress → quality_check → ready_for_pickup → completed
```

**POST request:**
```json
{
  "appointment_id": 1,
  "stage": "received",
  "description": "Vehicle received for inspection",
  "estimated_completion": "2024-01-20T17:00:00"
}
```

**PUT request (stage advance):**
```json
{
  "stage": "in_progress",
  "note": "Engine repair started",
  "estimated_completion": "2024-01-20T17:00:00"
}
```

---

#### Invoices

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/invoices/shops/{shop_id}` | Create invoice |
| `GET` | `/api/v1/invoices/shops/{shop_id}` | List shop invoices (filter by `status`) |
| `GET` | `/api/v1/invoices/shops/{shop_id}/{invoice_id}` | Invoice detail |
| `POST` | `/api/v1/invoices/shops/{shop_id}/{invoice_id}/send` | Send to customer |
| `POST` | `/api/v1/invoices/shops/{shop_id}/{invoice_id}/payments` | Record a payment |

`status` filter values: `draft` · `sent` · `paid` · `partially_paid` · `overdue` · `cancelled`

**POST /invoices request:**
```json
{
  "customer_id": 3,
  "appointment_id": 1,
  "items": [
    { "item_type": "labor", "name": "Oil Change Labor", "quantity": 1, "unit_price": 35 },
    { "item_type": "part",  "name": "Oil Filter",       "quantity": 1, "unit_price": 15 }
  ],
  "labor_cost": 35,
  "parts_cost": 15,
  "tax_amount": 5,
  "discount_amount": 0,
  "total_amount": 55,
  "due_date": "2024-01-30T00:00:00"
}
```

**POST /payments request:**
```json
{
  "amount": 55,
  "method": "cash",
  "reference": "REF-001",
  "notes": "Full payment received"
}
```

`method` values: `cash` · `card` · `transfer` · `mobile_payment` · `other`

---

#### Ratings — Analytics View

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/ratings/shops/{shop_id}/top-products` | Top-rated products in the shop |
| `GET` | `/api/v1/ratings/shops/{shop_id}/top-services` | Top-rated services in the shop |

**Response shape:**
```json
{
  "top_products": [
    { "product_id": 5, "name": "Oil Filter", "average_rating": 4.8, "total_ratings": 24 }
  ]
}
```

---

#### Notifications

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/mechanic/my-notifications` | Own notifications (filter `?status=unread`) |
| `PUT` | `/api/v1/mechanic/notifications/{notification_id}/read` | Mark as read |

Notification types received by owners: `new_booking` · `booking_cancelled` · `new_order` · `order_cancelled` · `payment_received`

---

### Shop Owner Capability Summary

| Domain | Create | Read | Update | Delete |
|--------|--------|------|--------|--------|
| Shop (own) | ✓ | ✓ | ✓ | ✓ (soft) |
| Members | ✓ add | ✓ list | ✓ role change | ✓ (soft) |
| Products | ✓ | ✓ | ✓ | ✓ (soft) |
| Services | ✓ | ✓ | ✓ | ✓ (soft) |
| Categories | ✓ | ✓ (public) | ✓ | ✓ |
| Bookings | — | ✓ pending, detail, today | ✓ accept/reject | — |
| Orders | — | ✓ pending | ✓ accept/reject, ready | — |
| Quotations | ✓ | ✓ | ✓ | — |
| Repair Progress | ✓ | ✓ | ✓ stage advance | — |
| Invoices | ✓ | ✓ | ✓ send, payment | — |
| Ratings | — | ✓ top products/services | — | — |
| Mechanic Performance | ✓ record | ✓ all mechanics, individual, top N, history | — | — |
| Notifications | — | ✓ | ✓ mark read | — |
| Chat | ✓ rooms | ✓ messages | ✓ send, read, close | — |

---

## Role Comparison at a Glance

| Capability | Admin | Shop Owner | Mechanic | Customer | Public |
|-----------|:-----:|:----------:|:--------:|:--------:|:------:|
| Manage any user account | ✓ | — | — | — | — |
| View platform statistics | ✓ | — | — | — | — |
| Hard-delete shops | ✓ | — | — | — | — |
| Moderate ratings | ✓ | — | — | — | — |
| Create / manage a shop | — | ✓ | — | — | — |
| Add / remove mechanics | — | ✓ | — | — | — |
| Manage products & services | — | ✓ | Read only | — | — |
| Accept / reject bookings | — | ✓ | ✓ | — | — |
| Create quotations & invoices | — | ✓ | ✓ | — | — |
| View mechanic performance | — | ✓ all | ✓ own only | — | — |
| Browse shops & products | — | ✓ | ✓ | ✓ | ✓ |
| Book appointments | — | — | — | ✓ | — |
| Rate products & services | — | — | — | ✓ | — |
