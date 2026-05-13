# Garage Management — API Documentation

## Quick Reference

| Symbol | Meaning |
|--------|---------|
| 🔒 | Requires `Authorization: Bearer <token>` |
| 👑 | Admin token required (`is_superuser = true`) |
| 🏪 | Shop owner token required |
| 🔧 | Shop owner **or** mechanic token required |

**Base URL (local):** `http://localhost:8000/api/v1`  
**Interactive docs:** `http://localhost:8000/docs`

**Date format:** ISO 8601 — `2024-01-15T10:30:00`  
**Price format:** Decimal — `39.99`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Shops](#2-shops)
3. [Shop Products](#3-shop-products)
4. [Shop Services](#4-shop-services)
5. [Categories](#5-categories)
6. [Vehicle Database (Public)](#6-vehicle-database-public)
7. [Customer Vehicles](#7-customer-vehicles)
8. [Browse Shop (Public)](#8-browse-shop-public)
9. [Unified Booking](#9-unified-booking)
10. [Customer Appointments](#10-customer-appointments)
11. [Customer Product Orders](#11-customer-product-orders)
12. [Mechanic / Shop — Bookings](#12-mechanic--shop--bookings)
13. [Mechanic / Shop — Orders](#13-mechanic--shop--orders)
14. [Notifications](#14-notifications)
15. [Quotations](#15-quotations)
16. [Repair Progress](#16-repair-progress)
17. [Invoices](#17-invoices)
18. [Chat / Support](#18-chat--support)
19. [Ratings](#19-ratings)
20. [Mechanic Performance](#20-mechanic-performance)
21. [Admin](#21-admin)
22. [Error Format & Status Codes](#error-format--status-codes)

---

## 1. Authentication

### Register
`POST /auth/register`

**Request**
```json
{
  "email": "user@example.com",
  "username": "newuser",
  "password": "password123",
  "full_name": "John Doe",
  "roles": "user",
  "is_active": true
}
```

**Response** `201`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "newuser",
  "full_name": "John Doe",
  "roles": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

---

### Login
`POST /auth/login`

**Content-Type:** `application/x-www-form-urlencoded`

**Body:** `username=customer1&password=customer123`

**Response** `200`
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

---

### Refresh Token
`POST /auth/refresh`

```json
{ "refresh_token": "eyJhbGci..." }
```

**Response** — same shape as login.

---

### Get Current User
`GET /auth/me` 🔒

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "customer1",
  "full_name": "Test Customer",
  "roles": "user",
  "is_active": true
}
```

---

### Get My Roles
`GET /auth/me/roles` 🔒

```json
{
  "username": "customer1",
  "roles": ["user"],
  "is_superuser": false
}
```

---

### Logout
`POST /auth/logout` 🔒

```json
{ "refresh_token": "eyJhbGci..." }
```

---

### Logout All Devices
`POST /auth/logout-all` 🔒

---

## 2. Shops

### List All Shops
`GET /shops` 🔒

```json
[
  {
    "id": 1,
    "name": "Test Garage",
    "address": "123 Test Street",
    "phone": "+1234567890",
    "email": "garage@test.com",
    "is_active": true
  }
]
```

---

### Get Shop Details
`GET /shops/{shop_id}` 🔒

---

### Create Shop
`POST /shops` 🔒

```json
{
  "name": "My Garage",
  "address": "456 Main St",
  "phone": "+1234567890",
  "email": "shop@example.com",
  "description": "Best garage in town"
}
```

---

### Update Shop
`PUT /shops/{shop_id}` 🔒 🏪

Same body as create.

---

### Delete Shop
`DELETE /shops/{shop_id}` 🔒 🏪

---

### My Shops
`GET /shops/my-shops` 🔒

Returns all shops where the current user is owner or mechanic.

```json
[
  { "shop_id": 1, "shop_name": "Test Garage", "role": "owner", "is_active": true }
]
```

---

### Shop Members

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/shops/{shop_id}/members` | 🔒 🔧 | List all members |
| `POST` | `/shops/{shop_id}/members` | 🔒 🏪 | Add member |
| `PUT` | `/shops/{shop_id}/members/{user_id}/role` | 🔒 🏪 | Change role |
| `DELETE` | `/shops/{shop_id}/members/{user_id}` | 🔒 🏪 | Remove member |

**Add Member request:**
```json
{ "user_id": 5, "shop_id": 1, "role": "mechanic" }
```
> `role` must be `"owner"` or `"mechanic"`.

---

## 3. Shop Products

> All write endpoints require shop owner. Read endpoints require shop member.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/shops/{shop_id}/products` | 🔒 🏪 | Create product |
| `GET` | `/shops/{shop_id}/products` | 🔒 🔧 | List products |
| `GET` | `/shops/{shop_id}/products/{product_id}` | 🔒 🔧 | Get product |
| `PUT` | `/shops/{shop_id}/products/{product_id}` | 🔒 🏪 | Update product |
| `DELETE` | `/shops/{shop_id}/products/{product_id}` | 🔒 🏪 | Delete product |
| `GET` | `/shops/{shop_id}/products/search` | 🔒 🔧 | Search products |
| `GET` | `/shops/{shop_id}/products/by-service/{service_id}` | 🔒 🔧 | Products for a service |
| `POST` | `/shops/{shop_id}/products/search-by-image` | 🔒 🔧 | Image search (upload) |

**Create / Update request:**
```json
{
  "name": "Synthetic Oil 5W-30",
  "description": "Full synthetic motor oil",
  "price": 29.99,
  "stock_quantity": 50,
  "category_id": 1,
  "sku": "OIL-5W30"
}
```

---

## 4. Shop Services

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/shops/{shop_id}/services` | 🔒 🏪 | Create service |
| `GET` | `/shops/{shop_id}/services` | 🔒 🔧 | List services |
| `GET` | `/shops/{shop_id}/services/{service_id}` | 🔒 🔧 | Get service |
| `PUT` | `/shops/{shop_id}/services/{service_id}` | 🔒 🏪 | Update service |
| `DELETE` | `/shops/{shop_id}/services/{service_id}` | 🔒 🏪 | Delete service |
| `GET` | `/shops/{shop_id}/services/by-type` | 🔒 🔧 | Filter by type |

**Create / Update request:**
```json
{
  "name": "Oil Change",
  "description": "Full oil change with filter",
  "price": 39.99,
  "duration_minutes": 30,
  "service_type": "shop_based",
  "mobile_service_fee": 0
}
```
> `service_type`: `"shop_based"` · `"mobile"`

---

## 5. Categories

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/categories` | 🔒 🏪 | Create category |
| `GET` | `/categories` | Public | List root categories |
| `GET` | `/categories/tree` | Public | Full nested tree |
| `GET` | `/categories/{category_id}` | Public | Get category |
| `GET` | `/categories/{category_id}/products` | Public | Products in category |
| `PUT` | `/categories/{category_id}` | 🔒 🏪 | Update category |
| `DELETE` | `/categories/{category_id}` | 🔒 🏪 | Delete category |
| `GET` | `/categories/by-service/{service_id}` | Public | Categories for a service |
| `POST` | `/categories/service-links` | 🔒 🏪 | Link category to service |

**Create category request:**
```json
{
  "name": "Engine Parts",
  "description": "...",
  "parent_id": null,
  "shop_id": 1
}
```

---

## 6. Vehicle Database (Public)

No authentication required.

### List Makes
`GET /vehicles/makes`

```json
[
  { "id": 1, "name": "Toyota", "country": "Japan" },
  { "id": 2, "name": "Honda",  "country": "Japan" }
]
```

---

### List Models by Make
`GET /vehicles/makes/{make_id}/models`

```json
[
  { "id": 1, "name": "Camry", "vehicle_type": "Sedan" }
]
```

---

### List Years by Model
`GET /vehicles/models/{model_id}/years`

```json
[
  { "id": 1, "year": 2020 },
  { "id": 2, "year": 2021 }
]
```

---

### List Engines by Year
`GET /vehicles/years/{year_id}/engines`

```json
[
  {
    "id": 1,
    "engine_code": "2.5L 4-Cyl",
    "displacement": "2.5L",
    "cylinders": 4,
    "fuel_type": "gasoline",
    "power_hp": 203
  }
]
```

---

### Additional Vehicle Endpoints

| Path | Description |
|------|-------------|
| `GET /vehicles/fuel-types` | List all fuel types |
| `GET /vehicles/hierarchy` | Full make → model → year tree |
| `GET /vehicles/search?q=camry` | Search vehicles by keyword |
| `GET /vehicles/validate?make=Toyota&model=Camry&year=2020` | Validate a vehicle combo |

---

## 7. Customer Vehicles

### Add Vehicle
`POST /my-vehicles` 🔒

```json
{
  "make": "Toyota",
  "model": "Camry",
  "year": 2020,
  "engine": "2.5L 4-Cyl",
  "fuel_type": "gasoline",
  "license_plate": "ABC-123",
  "color": "Silver",
  "mileage": 45000,
  "is_primary": true
}
```

---

### List My Vehicles
`GET /my-vehicles` 🔒

```json
[
  {
    "id": 1,
    "make": "Toyota",
    "model": "Camry",
    "year": 2020,
    "license_plate": "ABC-123",
    "is_primary": true
  }
]
```

---

### Other Vehicle Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/my-vehicles/{vehicle_id}` | Get one vehicle |
| `PUT` | `/my-vehicles/{vehicle_id}` | Update vehicle |
| `DELETE` | `/my-vehicles/{vehicle_id}` | Delete vehicle |
| `GET` | `/my-vehicles/primary` | Get primary vehicle |
| `POST` | `/my-vehicles/{vehicle_id}/set-primary` | Set as primary |
| `POST` | `/my-vehicles/filter-products` | Find compatible products |

---

## 8. Browse Shop (Public)

No authentication required.

### Browse Products
`GET /customers/shops/{shop_id}/browse/products`

| Query Param | Type | Description |
|-------------|------|-------------|
| `category_id` | integer | Filter by category *(optional)* |
| `q` | string | Search keyword *(optional)* |

```json
[
  {
    "id": 1,
    "name": "Synthetic Oil 5W-30",
    "description": "Full synthetic motor oil",
    "price": 29.99,
    "image_url": "...",
    "thumbnail_url": "..."
  }
]
```

---

### Browse Services
`GET /customers/shops/{shop_id}/browse/services`

```json
[
  {
    "id": 1,
    "name": "Oil Change",
    "description": "Full oil change with filter",
    "price": 39.99,
    "duration_minutes": 30,
    "image_url": "..."
  }
]
```

---

### Browse Shop Info
`GET /customers/shops/{shop_id}/browse/shop-info`

```json
{
  "id": 1,
  "name": "Test Garage",
  "description": "...",
  "address": "123 Test St",
  "phone": "+1234567890",
  "email": "garage@test.com"
}
```

---

## 9. Unified Booking

### Create Booking
`POST /product-orders/unified-booking` 🔒

Handles service-only, products-only, or combined bookings in a single request.

**Service Only**
```json
{
  "shop_id": 1,
  "service_id": 1,
  "appointment_date": "2024-01-15T10:00:00",
  "vehicle_info": "Toyota Camry 2020",
  "service_notes": "Please check brakes"
}
```

**Products Only**
```json
{
  "shop_id": 1,
  "product_items": [
    { "product_id": 1, "quantity": 2 }
  ],
  "pickup_date": "2024-01-16T14:00:00",
  "product_notes": "Call when ready"
}
```

**Combined (Service + Products)**
```json
{
  "shop_id": 1,
  "service_id": 1,
  "product_items": [{ "product_id": 1, "quantity": 1 }],
  "appointment_date": "2024-01-15T10:00:00",
  "pickup_date": "2024-01-16T14:00:00",
  "vehicle_info": "Toyota Camry 2020"
}
```

**Mobile Service (with location)**
```json
{
  "shop_id": 1,
  "service_id": 2,
  "appointment_date": "2024-01-15T10:00:00",
  "customer_address": "456 Home St",
  "customer_phone": "+1234567890",
  "customer_location_lat": 13.756,
  "customer_location_lng": 100.502
}
```

**Response** `201`
```json
{
  "message": "Combined booking created successfully",
  "shop_id": 1,
  "appointment": {
    "id": 1,
    "service_id": 1,
    "appointment_date": "2024-01-15T10:00:00",
    "status": "pending",
    "pricing": {
      "service_price": 39.99,
      "mobile_fee": 0,
      "discount": 0,
      "tax": 0,
      "total": 39.99
    }
  },
  "product_order": {
    "id": 2,
    "total_amount": 29.99,
    "status": "pending"
  }
}
```

---

### Calculate Price Preview
`POST /product-orders/calculate-price` 🔒

Same request body as **Create Booking**. Returns price breakdown **without** creating any records.

```json
{
  "service": {
    "id": 1,
    "name": "Oil Change",
    "price": 39.99,
    "type": "shop_based"
  },
  "products": [
    { "product_id": 1, "name": "Oil Filter", "unit_price": 15, "quantity": 1, "total_price": 15 }
  ],
  "pricing": {
    "service_price": 39.99,
    "mobile_service_fee": 0,
    "products_subtotal": 15,
    "subtotal": 54.99,
    "discount_amount": 0,
    "tax_amount": 0,
    "total_amount": 54.99
  }
}
```

---

## 10. Customer Appointments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/customers/my-appointments` | 🔒 | List my appointments |
| `GET` | `/customers/my-appointments/{appointment_id}` | 🔒 | Get appointment detail |
| `PUT` | `/customers/my-appointments/{appointment_id}/cancel` | 🔒 | Cancel appointment |
| `GET` | `/customers/my-service-history` | 🔒 | Full service history |
| `GET` | `/customers/shops/{shop_id}/appointments` | 🔒 🔧 | Shop's appointments list |
| `PUT` | `/customers/shops/{shop_id}/appointments/{appointment_id}/status` | 🔒 🔧 | Update status |

**List my appointments — query params:**

| Param | Values |
|-------|--------|
| `status` | `pending` · `confirmed` · `completed` · `cancelled` |

---

## 11. Customer Product Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/product-orders/my-orders` | 🔒 | List my orders |
| `GET` | `/product-orders/my-orders/{order_id}` | 🔒 | Order details |
| `GET` | `/product-orders/my-orders/{order_id}/price-breakdown` | 🔒 | Price breakdown |
| `PUT` | `/product-orders/my-orders/{order_id}/cancel` | 🔒 | Cancel order |
| `GET` | `/product-orders/shops/{shop_id}/orders` | 🔒 🔧 | Shop's orders |
| `PUT` | `/product-orders/shops/{shop_id}/orders/{order_id}/status` | 🔒 🔧 | Update order status |

**List my orders — query param:**

| Param | Values |
|-------|--------|
| `order_status` | `pending` · `confirmed` · `processing` · `ready` · `completed` · `cancelled` |

---

## 12. Mechanic / Shop — Bookings

### View Pending Bookings
`GET /mechanic/shops/{shop_id}/pending-bookings` 🔒 🔧

```json
{
  "count": 2,
  "bookings": [
    {
      "appointment_id": 1,
      "customer": { "id": 3, "name": "John Doe", "phone": "customer1" },
      "vehicle_info": "Toyota Camry 2020",
      "appointment_date": "2024-01-15T10:00:00",
      "total_amount": 39.99,
      "notes": null
    }
  ]
}
```

---

### View Booking Details
`GET /mechanic/shops/{shop_id}/bookings/{appointment_id}` 🔒 🔧

---

### Accept / Reject Booking
`POST /mechanic/shops/{shop_id}/bookings/{appointment_id}/action` 🔒 🔧

**Accept**
```json
{ "action": "accept", "notes": "We'll start at 10 AM" }
```

**Reject**
```json
{ "action": "reject", "reason": "Fully booked that day" }
```

---

### Today's Bookings
`GET /mechanic/shops/{shop_id}/today-bookings` 🔒 🔧

---

## 13. Mechanic / Shop — Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/mechanic/shops/{shop_id}/pending-orders` | 🔒 🔧 | Pending product orders |
| `POST` | `/mechanic/shops/{shop_id}/orders/{order_id}/action` | 🔒 🔧 | Accept / reject order |
| `PUT` | `/mechanic/shops/{shop_id}/orders/{order_id}/ready` | 🔒 🔧 | Mark order ready for pickup |

**Accept / Reject order:**
```json
{ "action": "accept" }
```
or
```json
{ "action": "reject", "reason": "Out of stock" }
```

---

## 14. Notifications

### My Notifications
`GET /mechanic/my-notifications` 🔒

| Query Param | Values | Default |
|-------------|--------|---------|
| `status` | `unread` · `read` | — |
| `limit` | integer | `50` (max `100`) |

```json
{
  "unread_count": 3,
  "notifications": [
    {
      "id": 1,
      "type": "new_booking",
      "title": "New Booking Received",
      "message": "John booked Oil Change",
      "status": "unread",
      "appointment_id": 1,
      "created_at": "2024-01-01T10:00:00",
      "read_at": null
    }
  ]
}
```

---

### Mark as Read
`PUT /mechanic/notifications/{notification_id}/read` 🔒

---

## 15. Quotations

### Shop — Create Quotation
`POST /quotations/shops/{shop_id}` 🔒 🔧

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

### Shop — Other Quotation Actions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/quotations/shops/{shop_id}` | 🔒 🔧 | List shop quotations |
| `GET` | `/quotations/shops/{shop_id}/{quotation_id}` | 🔒 🔧 | Get quotation detail |
| `PUT` | `/quotations/shops/{shop_id}/{quotation_id}` | 🔒 🔧 | Update quotation |
| `POST` | `/quotations/shops/{shop_id}/{quotation_id}/send` | 🔒 🔧 | Send to customer |

**List shop quotations — query param:**

| Param | Values |
|-------|--------|
| `status` | `draft` · `sent` · `approved` · `rejected` · `expired` |

---

### Customer — Quotation Actions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/quotations/my-quotations` | 🔒 | View my quotations |
| `GET` | `/quotations/my-quotations/{quotation_id}` | 🔒 | Quotation detail |
| `POST` | `/quotations/my-quotations/{quotation_id}/action` | 🔒 | Approve / reject |

**Approve:**
```json
{ "action": "approve" }
```

**Reject:**
```json
{ "action": "reject", "rejection_reason": "Too expensive" }
```

---

## 16. Repair Progress

**Stages (in order):**  
`received` → `diagnosing` → `waiting_parts` → `in_progress` → `quality_check` → `ready_for_pickup` → `completed`

### Shop — Create Progress Record
`POST /repair-progress/shops/{shop_id}` 🔒 🔧

```json
{
  "appointment_id": 1,
  "stage": "received",
  "description": "Vehicle received for inspection",
  "estimated_completion": "2024-01-20T17:00:00"
}
```

---

### Shop — Update Stage
`PUT /repair-progress/shops/{shop_id}/{progress_id}` 🔒 🔧

```json
{
  "stage": "in_progress",
  "note": "Engine repair started",
  "estimated_completion": "2024-01-20T17:00:00"
}
```

---

### Shop — List All Repairs
`GET /repair-progress/shops/{shop_id}` 🔒 🔧

| Query Param | Values |
|-------------|--------|
| `stage` | `received` · `diagnosing` · `waiting_parts` · `in_progress` · `quality_check` · `ready_for_pickup` · `completed` |

---

### Customer — View My Repairs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/repair-progress/my-repairs` | List all my repairs |
| `GET` | `/repair-progress/my-repairs/{progress_id}` | Detail with full update history |

**Detail response:**
```json
{
  "id": 1,
  "stage": "in_progress",
  "description": "Engine repair",
  "estimated_completion": "2024-01-20T17:00:00",
  "updates": [
    {
      "id": 1,
      "from_stage": "received",
      "to_stage": "diagnosing",
      "note": "Found engine issue",
      "created_at": "2024-01-15T10:00:00"
    }
  ]
}
```

---

## 17. Invoices

### Shop — Create Invoice
`POST /invoices/shops/{shop_id}` 🔒 🔧

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

---

### Shop — Other Invoice Actions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/invoices/shops/{shop_id}` | 🔒 🔧 | List shop invoices |
| `GET` | `/invoices/shops/{shop_id}/{invoice_id}` | 🔒 🔧 | Invoice detail |
| `POST` | `/invoices/shops/{shop_id}/{invoice_id}/send` | 🔒 🔧 | Send to customer |
| `POST` | `/invoices/shops/{shop_id}/{invoice_id}/payments` | 🔒 🔧 | Record payment |

**Record payment:**
```json
{
  "amount": 55,
  "method": "cash",
  "reference": "REF-001",
  "notes": "Full payment"
}
```
**Payment methods:** `cash` · `card` · `transfer` · `mobile_payment` · `other`

**List invoices — query param:**

| Param | Values |
|-------|--------|
| `status` | `draft` · `sent` · `paid` · `partially_paid` · `overdue` · `cancelled` |

---

### Customer — Invoices

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/invoices/my-invoices` | List my invoices |
| `GET` | `/invoices/my-invoices/{invoice_id}` | Invoice detail with payments |

---

## 18. Chat / Support

### Create Chat Room
`POST /chat/rooms` 🔒

```json
{
  "shop_id": 1,
  "room_type": "appointment",
  "appointment_id": 1
}
```
**Room types:** `general` · `appointment` · `order`

---

### List My Chat Rooms
`GET /chat/rooms` 🔒

```json
[
  {
    "id": 1,
    "shop": { "id": 1, "name": "Test Garage" },
    "room_type": "appointment",
    "last_message": {
      "sender_id": 3,
      "content": "When will my car be ready?",
      "created_at": "2024-01-15T10:00:00"
    },
    "unread_count": 2
  }
]
```

---

### View Room Messages
`GET /chat/rooms/{room_id}` 🔒

| Query Param | Default |
|-------------|---------|
| `limit` | `50` |

---

### Send Message
`POST /chat/rooms/{room_id}/messages` 🔒

```json
{
  "content": "When will my car be ready?",
  "message_type": "text"
}
```
**Message types:** `text` · `image` · `file` · `system`

---

### Other Chat Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/chat/rooms/{room_id}/messages/{message_id}/read` | Mark message as read |
| `GET` | `/chat/rooms/{room_id}/unread-count` | Get unread count |
| `PUT` | `/chat/rooms/{room_id}/close` | Close chat room |

---

## 19. Ratings

### Rate a Product
`POST /ratings/products` 🔒

```json
{
  "product_id": 1,
  "rating": 5,
  "review": "Great oil!",
  "order_id": 2
}
```

---

### Rate a Service
`POST /ratings/services` 🔒

```json
{
  "service_id": 1,
  "rating": 5,
  "review": "Quick and thorough",
  "appointment_id": 1
}
```

---

### Other Rating Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/ratings/products/{product_id}/summary` | Public | Rating summary |
| `GET` | `/ratings/products/{product_id}/reviews` | Public | Reviews list |
| `GET` | `/ratings/services/{service_id}/summary` | Public | Rating summary |
| `GET` | `/ratings/services/{service_id}/reviews` | Public | Reviews list |
| `GET` | `/ratings/shops/{shop_id}/top-products` | 🔒 🏪 | Top-rated products |
| `GET` | `/ratings/shops/{shop_id}/top-services` | 🔒 🏪 | Top-rated services |
| `GET` | `/ratings/my-ratings` | 🔒 | All my submitted ratings |

**Rating summary response:**
```json
{
  "average_rating": 4.5,
  "total_ratings": 12,
  "five_star": 8,
  "four_star": 3,
  "three_star": 1,
  "two_star": 0,
  "one_star": 0
}
```

---

## 20. Mechanic Performance

### Owner — All Mechanics Overview
`GET /shops/{shop_id}/mechanics/performance` 🔒 🏪

| Query Param | Format | Description |
|-------------|--------|-------------|
| `date_from` | `YYYY-MM-DD` | Default: last 30 days |
| `date_to` | `YYYY-MM-DD` | Default: today |

```json
{
  "shop_summary": {
    "total_jobs": 45,
    "total_revenue": 2250.00,
    "mechanic_count": 3
  },
  "mechanics": [...],
  "total_mechanics": 3
}
```

---

### Owner — Top Mechanics
`GET /shops/{shop_id}/mechanics/performance/top` 🔒 🏪

| Query Param | Values | Default |
|-------------|--------|---------|
| `metric` | `revenue` · `rating` · `jobs` | `revenue` |
| `limit` | 1–20 | `5` |

---

### Owner — Individual Mechanic
`GET /shops/{shop_id}/mechanics/{mechanic_id}/performance` 🔒 🏪

---

### Owner — Full History (Paginated)
`GET /shops/{shop_id}/mechanics/{mechanic_id}/performance/history` 🔒 🏪

| Query Param | Default |
|-------------|---------|
| `page` | `1` |
| `page_size` | `20` (max `100`) |

---

### Owner — Record Performance
`POST /shops/{shop_id}/mechanics/{mechanic_id}/performance/record` 🔒 🏪

```json
{
  "appointment_id": 1,
  "service_name": "Oil Change",
  "revenue_generated": 39.99,
  "estimated_duration": 30,
  "actual_duration": 25
}
```

---

### Customer — Rate a Mechanic
`POST /shops/{shop_id}/mechanics/{mechanic_id}/rate` 🔒

```json
{
  "appointment_id": 1,
  "rating": 5,
  "review": "Very professional!"
}
```

---

### Mechanic — My Own Performance
`GET /shops/{shop_id}/mechanics/my-performance` 🔒 🔧

Returns own summary + rank within the shop.

---

## 21. Admin

> All admin endpoints require a superuser token (`is_superuser = true`).

### Users

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | List all users (paginated) |
| `GET` | `/admin/users/{user_id}` | User detail |
| `PUT` | `/admin/users/{user_id}/role` | Change user role |
| `PUT` | `/admin/users/{user_id}/status` | Activate / deactivate |
| `DELETE` | `/admin/users/{user_id}` | Delete user |

**List users — query params:**

| Param | Type | Description |
|-------|------|-------------|
| `skip` | integer | Offset (default `0`) |
| `limit` | integer | Page size (default `100`, max `1000`) |
| `search` | string | Search username / email / name |
| `is_active` | boolean | Filter active/inactive |
| `is_superuser` | boolean | Filter admins |

---

### Shops

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/shops` | List all shops |
| `GET` | `/admin/shops/{shop_id}` | Shop detail |
| `DELETE` | `/admin/shops/{shop_id}` | Delete shop |

---

### Bookings & Orders

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/appointments` | All appointments (paginated) |
| `GET` | `/admin/orders` | All product orders |

---

### Ratings

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/ratings` | All ratings |
| `DELETE` | `/admin/ratings/product/{rating_id}` | Delete product rating |
| `DELETE` | `/admin/ratings/service/{rating_id}` | Delete service rating |

---

### Statistics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/statistics` | Platform overview totals |
| `GET` | `/admin/statistics/daily` | Daily stats (query param: `days=30`) |

**Statistics response:**
```json
{
  "total_users": 150,
  "total_shops": 12,
  "total_appointments": 380,
  "total_revenue": 15240.50
}
```

---

## Error Format & Status Codes

**All errors return:**
```json
{ "detail": "Error message here" }
```

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `400` | Bad Request — validation or business rule violation |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — valid token but insufficient permissions |
| `404` | Not Found |
| `422` | Unprocessable Entity — request body schema error |
| `500` | Internal Server Error |

---

## Test Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Shop Owner | `owner1` | `owner123` |
| Mechanic | `mechanic1` | `mechanic123` |
| Customer | `customer1` | `customer123` |

> 🔒 = Requires `Authorization: Bearer <token>` header
