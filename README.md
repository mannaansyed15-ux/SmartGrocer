# SmartGrocer — Intelligent Grocery Store Management & Billing System

A Flask + SQLAlchemy + SQLite grocery POS and inventory system designed for SIH demonstrations. It includes authenticated admin/cashier access, real database-backed dashboard, product/customer CRUD, catalogue, POS checkout, GST/discount calculations, invoices, PDF receipts, inventory transactions, sales history, analytics, explainable restock suggestions and expiry intelligence.

## Setup

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```
Open `http://127.0.0.1:5000`.

## Demo credentials
- Admin: `admin` / `admin123`
- Cashier: `cashier` / `cashier123`

Admin can delete products/customers; cashier can operate the POS and view operational pages.

## Architecture
`app/models.py` contains normalized SQLAlchemy models. `app/routes/main.py` contains authenticated routes and authoritative checkout logic. `app/services/analytics.py` contains explainable restock and sales-series logic. Templates and vanilla JS live under `app/templates` and `app/static`.

## Checkout integrity
The browser sends only product IDs/quantities, customer, discount and payment method. The server reloads prices/GST/stock, validates quantities, computes all monetary values with `Decimal`, creates Bill/BillItems/Payment/InventoryTransaction, reduces stock and updates customer totals in one transaction. Failures roll back.

## Intelligence
Restock uses units sold over 30 days and estimates a 14-day demand horizon. Expiry status is calculated from each product's stored expiry date. Analytics are direct database aggregations.

## Tests
Run:
```bash
pytest -q
```

## Limitations
Camera barcode scanning is intentionally not required; barcode keyboard/scanner input is supported. Product editing is implemented as an admin-friendly modal but customer editing is not yet exposed as a separate UI form; customer creation/deletion and purchase history are functional. For a production deployment, add CSRF protection, stronger secret management, migrations, audit logging and a real payment gateway.
