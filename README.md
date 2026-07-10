# Logistics System (Frappe App)

A backend system for managing delivery orders and delivery runs: building runs,
assigning drivers, executing deliveries stop-by-stop, and banking collected cash —
with role-based access control for Managers, Dispatchers, and Drivers.

Built on **Frappe Framework**.

---

## 1. Setup, Installation & Migration

### Prerequisites
- `bench` (Frappe Bench CLI) already set up, or install one following the
  [official Frappe install guide](https://frappeframework.com/docs/user/en/installation).
- Python 3.10+, Node 18+, MariaDB 10.6+, Redis.

### Steps

```bash
# 1. Create a bench (skip if you already have one)
bench init logistics-bench --frappe-branch version-15
cd logistics-bench

# 2. Get this app
bench get-app logistics_system /path/to/this/repo
# or, once pushed to GitHub:
# bench get-app https://github.com/<your-username>/logistics-system.git

# 3. Create a new site (or use an existing one)
bench new-site logistics.localhost

# 4. Install the app on the site
bench --site logistics.localhost install-app logistics_system

# 5. Run migrations (creates all DocType tables)
bench --site logistics.localhost migrate

# 6. Start the dev server
bench start
```

Then open `http://logistics.localhost:8000/app` and log in as `Administrator`.

### Post-install
`install-app` automatically creates three Roles via the `after_install` hook:
`Logistics Manager`, `Logistics Dispatcher`, `Driver`.

To assign a driver's system login: open **Driver** doctype, set the `Linked User`
field to the corresponding `User` record (this is how the API knows which driver
a logged-in "Driver" role user is allowed to act as).

### Running tests
```bash
bench --site logistics.localhost run-tests --app logistics_system
```

---

## 2. Backend Design

### App structure
```
logistics_system/
├── logistics/
│   ├── doctype/
│   │   ├── driver/            # Driver DocType
│   │   ├── order/              # Order DocType
│   │   ├── delivery_run/       # Delivery Run DocType (workflow lives here)
│   │   └── delivery_stop/      # Delivery Stop - child table of Delivery Run
│   └── page/logistics_dashboard/   # Bonus: dashboard page
├── api/
│   └── logistics_api.py        # Whitelisted REST endpoints (the public API surface)
├── permissions/
│   └── driver_permissions.py   # permission_query_conditions / has_permission for Driver role
├── setup/install.py            # after_install: creates the 3 roles
└── hooks.py
```

### Data model & relationships
- **Driver** — standalone master. `status` is a derived/read-only field, only ever
  changed by the workflow (never edited directly by users).
- **Order** — standalone master, one row per customer delivery. `status`,
  `assigned_driver`, and `delivery_run` are read-only and only mutated through
  the Run lifecycle actions.
- **Delivery Run** — the aggregate root of a driver's trip. Owns a child table,
  **Delivery Stop**, one row per order assigned to that run, in sequence order.
  `Delivery Stop` fetches `customer_name` / `address` / `cash_amount` from the
  linked Order (read-only fetch fields) so the run is a self-contained snapshot
  even if the Order record changes later.
- `Order.delivery_run` + `Delivery Stop.related_order` form a two-way link so you
  can navigate from either side.

### Why business logic lives on the `Delivery Run` document, not in the API layer
Each lifecycle step (`build_run`, `start_run`, `mark_stop_delivered`,
`mark_stop_failed`, `complete_run`, `bank_cash`) is a **whitelisted method on the
`DeliveryRun` document class**. The thin functions in `api/logistics_api.py` only:
1. resolve/create the document,
2. run permission checks (including the Driver-can-only-touch-their-own-run
   check),
3. call the document method,
4. shape the JSON response.

This keeps validation and state transitions colocated with the model they
mutate (testable via `frappe.get_doc(...).build_run(...)` directly, without HTTP),
while the API layer stays a thin, easily-securable boundary.

### Transaction safety
Frappe wraps each whitelisted request in a single DB transaction: it commits on
a 200 response, and **rolls back automatically** if any exception (including
`frappe.throw`) is raised during the request. Because every lifecycle method
raises via `frappe.throw` on any invalid state instead of partially saving, a
failed action (e.g. "driver already on run") never leaves the Run, Order, and
Driver records inconsistent with each other.

### Validation summary
| Rule | Where enforced |
|---|---|
| Phone required for Driver | `Driver.validate()` |
| Customer Name & Address required for Order | `Order.validate()` |
| Max Stops Per Run > 0 | `Driver.validate()` |
| Order cash amount ≥ 0 | `Order.validate()`, `DeliveryStop.validate()` |
| Inactive / On-Run driver can't be (re)assigned | `DeliveryRun._validate_driver_available()` |
| Only Open orders assignable | `DeliveryRun._select_orders_for_run()` |
| Orders per run ≤ driver's max stops | `DeliveryRun._select_orders_for_run()` |
| Failed stop requires a reason | `DeliveryStop.validate()` + `mark_stop_failed()` |
| Run can only complete when all stops resolved | `DeliveryRun.complete_run()` |

---

## 3. Status Flow

### Delivery Run
```
Draft --(build_run)--> Assigned --(start_run)--> En Route --(complete_run, all stops resolved)--> Completed --(bank_cash)--> Cash Banked
```
`Cancelled` is a reserved terminal state for manual cancellation from the Desk
(not wired to an API action in this submission — see Assumptions).

### Order
```
Open --(build_run)--> Assigned --(start_run)--> En Route --(mark_stop_delivered/failed)--> Delivered/Failed --(bank_cash, only if Delivered)--> Cash Banked
```

### Delivery Stop (per stop, inside a run)
```
Assigned --(start_run)--> En Route --(mark_stop_delivered)--> Delivered
                                   --(mark_stop_failed)-----> Failed
```

### Driver
```
Available --(start_run)--> On Run --(complete_run)--> Available
```
An `Inactive` driver (via the `Active` checkbox) cannot enter this cycle at all.

---

## 4. API Reference

All endpoints are POST (except the dashboard) and require an authenticated
Frappe session (cookie or API key/secret).

| Endpoint | Purpose |
|---|---|
| `POST /api/method/logistics_system.api.logistics_api.build_delivery_run` | `driver`, `order_names[]` (optional — auto-selects by priority if omitted) |
| `POST /api/method/logistics_system.api.logistics_api.start_delivery_run` | `run_name` |
| `POST /api/method/logistics_system.api.logistics_api.mark_stop_delivered` | `run_name`, `stop_name` |
| `POST /api/method/logistics_system.api.logistics_api.mark_stop_failed` | `run_name`, `stop_name`, `failed_reason` |
| `POST /api/method/logistics_system.api.logistics_api.complete_delivery_run` | `run_name` |
| `POST /api/method/logistics_system.api.logistics_api.bank_cash` | `run_name`, `cash_banked_location` |
| `GET /api/method/logistics_system.api.logistics_api.dashboard_summary` | KPI + active runs (bonus) |

Errors raised with `frappe.throw(...)` return Frappe's standard JSON error
envelope with a clear `message` and a non-2xx HTTP status
(`417` for validation errors, `403` for `frappe.PermissionError`, `404` if the
document doesn't exist).

---

## 5. Role-Based Access Control

| Role | Permissions |
|---|---|
| **Logistics Manager** | Full CRUD on Driver, Order, Delivery Run. |
| **Logistics Dispatcher** | Create/edit Orders and Drivers; build & start Delivery Runs (no delete rights). |
| **Driver** | Read-only on Order and Driver; can only *read/update* stops on the **Delivery Run linked to their own Driver record** (enforced by `permission_query_conditions` + `has_permission` in `permissions/driver_permissions.py`, plus an explicit ownership check inside the API layer). Cannot bank cash. |

A Driver's identity is resolved via `Driver.user` (a `Link` to `User`) —
whichever Driver record has `user == frappe.session.user` is "their" driver.

---

## 6. Assumptions

1. **"Workflow" is implemented as a code-enforced state machine** on the
   `Delivery Run` document (explicit `@frappe.whitelist()` transition methods)
   rather than Frappe's declarative Workflow DocType. This was a deliberate
   choice: the transitions here have side effects across three DocTypes
   (Run, Order, Driver) plus business validation that doesn't map cleanly onto
   the Workflow DocType's linear "state + action" model — a plain Python state
   machine keeps that multi-document logic in one clearly testable place.
2. Orders can be auto-selected into a run (`order_names` omitted) using
   priority (High → Medium → Low) then creation date as tie-breaker, or
   explicitly chosen by the dispatcher.
3. `Cancelled` run status exists in the schema (per the spec's status list) but
   no dedicated cancel action was implemented, since it wasn't in the "Workflow:
   Run Lifecycle" list of required actions — it's available for future Desk-level
   manual use.
4. Only `Delivered` stops contribute to `Total Cash Collected` and only
   `Delivered` orders move to `Cash Banked`; `Failed` orders remain `Failed`
   after cash banking, since no cash was collected for them.
5. A driver's `status` field is read-only in the UI/API and only ever changed
   by the lifecycle methods, to prevent it from drifting out of sync with
   actual run state.

---

## 7. Bonus: Dashboard

A Desk page at **Logistics Dashboard** (`/app/logistics-dashboard`) shows: open
orders, active drivers, runs en route, cash collected today, a list of active
runs, and a "Build Run" quick action dialog (driver + optional order picker)
that calls `build_delivery_run` directly.
