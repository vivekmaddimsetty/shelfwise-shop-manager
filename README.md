# Shelfwise

Shelfwise is a small-shop inventory and order manager. It helps a shop owner see what is in stock, record an order, and avoid selling stock that is no longer available.

## Run it

Requires Python 3.10 or newer. The app uses only Python's standard library, so no package installation is needed.

On Windows, double-click `run.bat` to start the server. Keep its window open while using the app.

```powershell
python backend/server.py
```

Run that command from the project folder. Open <http://127.0.0.1:8000>. The first run creates a local SQLite database at `data/shelfwise.db` and seeds a few sample products. Stop the server with Ctrl+C.

To start with a clean sample database, stop the server and remove `data/shelfwise.db`; it will be recreated on the next start.

## What is included

- Dashboard with product, order, revenue, and low-stock summaries.
- Searchable inventory with product creation and stock updates.
- Order creation with multiple products and quantities.
- Order cancellation that returns its items to stock.
- SQLite persistence and transaction-safe stock deduction.
- Responsive layout for laptop and mobile screens.

## Stock safety

Creating an order runs inside a SQLite `BEGIN IMMEDIATE` transaction. The server checks each product's current stock, deducts the requested quantity, and creates the order and its lines as one unit. If any item is unavailable, the transaction rolls back, so no partial order or partial stock deduction remains. Cancellation uses a transaction too and can only happen once for a placed order.

## Project structure

```text
backend/server.py       HTTP API, validation, SQLite schema, transaction rules
frontend/index.html     App structure
frontend/styles.css     Responsive visual design
frontend/app.js         UI state and API calls
data/                   Local SQLite database (created on first run)
tools/package_zip.py    Creates a clean source ZIP for sharing or downloading
```

Create a clean ZIP from the project folder with `python tools/package_zip.py`. The archive excludes the local database and temporary files.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/dashboard` | Summary metrics and recent activity |
| GET | `/api/products?search=...` | List and search products |
| POST | `/api/products` | Add a product |
| PATCH | `/api/products/{id}` | Update product fields or stock |
| GET | `/api/orders` | List orders |
| POST | `/api/orders` | Place an order |
| POST | `/api/orders/{id}/cancel` | Cancel and restock a placed order |

Invalid input returns `400`, missing records return `404`, and insufficient stock returns `409 Conflict`.

## Interview walkthrough

Start with the customer problem: a small shop needs a simple way to know what can be sold. Show the inventory and order flow, then explain the race condition that can happen when two orders request the last item. Shelfwise protects that rule with a database transaction and rolls back the whole order if stock is insufficient. Finish by describing how you would extend it with authentication, audit history, and automated tests.

This is a learning/demo project. It does not include authentication, deployment configuration, or production-grade backups yet.
