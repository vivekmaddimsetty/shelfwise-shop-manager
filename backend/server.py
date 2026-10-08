from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("SHELFWISE_DB", DATA_DIR / "shelfwise.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


def initialize_database() -> None:
    with closing(connect()) as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'General',
                price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                stock INTEGER NOT NULL CHECK(stock >= 0),
                reorder_level INTEGER NOT NULL DEFAULT 5 CHECK(reorder_level >= 0),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('placed', 'cancelled')),
                total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
            CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
            """
        )
        if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            samples = [
                ("Ceramic Travel Mug", "MUG-104", "Home & Living", 1899, 24, 6),
                ("Canvas Market Tote", "BAG-208", "Accessories", 1450, 8, 10),
                ("Desk Plant Set", "PLT-031", "Home & Living", 2499, 14, 5),
                ("Weekend Notebook", "PAP-115", "Stationery", 899, 3, 8),
                ("Linen Apron", "KIT-072", "Kitchen", 3200, 19, 5),
            ]
            db.executemany(
                "INSERT INTO products(name, sku, category, price_cents, stock, reorder_level, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(*item, now_iso()) for item in samples],
            )


def product_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "sku": row["sku"],
        "category": row["category"],
        "priceCents": row["price_cents"],
        "stock": row["stock"],
        "reorderLevel": row["reorder_level"],
        "createdAt": row["created_at"],
    }


def order_rows(db: sqlite3.Connection, limit: int | None = None) -> list[dict]:
    suffix = " LIMIT ?" if limit is not None else ""
    args = (limit,) if limit is not None else ()
    rows = db.execute(
        "SELECT o.id, o.customer, o.status, o.total_cents, o.created_at, "
        "COALESCE(SUM(i.quantity), 0) AS item_count "
        "FROM orders o LEFT JOIN order_items i ON i.order_id = o.id "
        "GROUP BY o.id ORDER BY o.id DESC" + suffix,
        args,
    ).fetchall()
    result = []
    for row in rows:
        items = db.execute(
            "SELECT product_name AS name, quantity, unit_price_cents AS unitPriceCents "
            "FROM order_items WHERE order_id = ? ORDER BY id",
            (row["id"],),
        ).fetchall()
        result.append(
            {
                "id": row["id"],
                "orderNumber": f"SW-{row['id']:04d}",
                "customer": row["customer"],
                "status": row["status"],
                "totalCents": row["total_cents"],
                "itemCount": row["item_count"],
                "createdAt": row["created_at"],
                "items": [dict(item) for item in items],
            }
        )
    return result


def validate_text(value, field: str, max_length: int = 100) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"{field} is required.")
    result = value.strip()
    if len(result) > max_length:
        raise ApiError(400, f"{field} must be {max_length} characters or fewer.")
    return result


def validate_nonnegative_int(value, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ApiError(400, f"{field} must be a whole number of at least {minimum}.")
    return value


class Handler(BaseHTTPRequestHandler):
    server_version = "Shelfwise/1.0"

    def log_message(self, format_string, *args):
        print(f"[{self.log_date_time_string()}] {format_string % args}")

    def send_json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ApiError(413, "Request body is too large.")
            value = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            raise ApiError(400, "Request body must be valid JSON.") from None
        if not isinstance(value, dict):
            raise ApiError(400, "Request body must be a JSON object.")
        return value

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/dashboard":
                return self.dashboard()
            if parsed.path == "/api/products":
                return self.products(parse_qs(parsed.query))
            if parsed.path == "/api/orders":
                with closing(connect()) as db:
                    return self.send_json(200, order_rows(db))
            return self.serve_frontend(parsed.path)
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except Exception:
            self.send_json(500, {"error": "Something went wrong. Please try again."})
            raise

    def do_POST(self):
        try:
            if self.path == "/api/products":
                return self.create_product(self.read_json())
            if self.path == "/api/orders":
                return self.create_order(self.read_json())
            match = re.fullmatch(r"/api/orders/(\d+)/cancel", self.path)
            if match:
                return self.cancel_order(int(match.group(1)))
            raise ApiError(404, "Endpoint not found.")
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except sqlite3.IntegrityError as error:
            self.send_json(409, {"error": "That SKU is already in use."})
        except Exception:
            self.send_json(500, {"error": "Something went wrong. Please try again."})
            raise

    def do_PATCH(self):
        try:
            match = re.fullmatch(r"/api/products/(\d+)", self.path)
            if not match:
                raise ApiError(404, "Endpoint not found.")
            return self.update_product(int(match.group(1)), self.read_json())
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except sqlite3.IntegrityError:
            self.send_json(409, {"error": "That SKU is already in use."})
        except Exception:
            self.send_json(500, {"error": "Something went wrong. Please try again."})
            raise

    def serve_frontend(self, path: str):
        requested = unquote(path)
        if requested in ("/", "/index.html"):
            file_path = FRONTEND / "index.html"
        elif requested in ("/app.js", "/styles.css"):
            file_path = FRONTEND / requested.lstrip("/")
        else:
            raise ApiError(404, "Page not found.")
        body = file_path.read_bytes()
        content_type = "text/html" if file_path.suffix == ".html" else (
            "text/javascript" if file_path.suffix == ".js" else "text/css"
        )
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def dashboard(self):
        with closing(connect()) as db:
            product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            low_stock_count = db.execute(
                "SELECT COUNT(*) FROM products WHERE stock <= reorder_level"
            ).fetchone()[0]
            order_count = db.execute(
                "SELECT COUNT(*) FROM orders WHERE status = 'placed'"
            ).fetchone()[0]
            sales_cents = db.execute(
                "SELECT COALESCE(SUM(total_cents), 0) FROM orders WHERE status = 'placed'"
            ).fetchone()[0]
            low_stock = [
                product_dict(row)
                for row in db.execute(
                    "SELECT * FROM products WHERE stock <= reorder_level "
                    "ORDER BY stock ASC, name ASC LIMIT 6"
                ).fetchall()
            ]
            return self.send_json(
                200,
                {
                    "productCount": product_count,
                    "lowStockCount": low_stock_count,
                    "orderCount": order_count,
                    "salesCents": sales_cents,
                    "lowStockProducts": low_stock,
                    "recentOrders": order_rows(db, 5),
                },
            )

    def products(self, query):
        search = query.get("search", [""])[0].strip()
        with closing(connect()) as db:
            rows = db.execute(
                "SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? OR category LIKE ? "
                "ORDER BY name COLLATE NOCASE",
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            ).fetchall()
            return self.send_json(200, [product_dict(row) for row in rows])

    def create_product(self, data):
        name = validate_text(data.get("name"), "Product name")
        sku = validate_text(data.get("sku"), "SKU", 40).upper()
        category = validate_text(data.get("category", "General"), "Category", 60)
        price_cents = validate_nonnegative_int(data.get("priceCents"), "Price")
        stock = validate_nonnegative_int(data.get("stock"), "Stock")
        reorder_level = validate_nonnegative_int(data.get("reorderLevel", 5), "Reorder level")
        with closing(connect()) as db:
            cursor = db.execute(
                "INSERT INTO products(name, sku, category, price_cents, stock, reorder_level, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, sku, category, price_cents, stock, reorder_level, now_iso()),
            )
            row = db.execute("SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self.send_json(201, product_dict(row))

    def update_product(self, product_id: int, data):
        allowed = {"name", "sku", "category", "priceCents", "stock", "reorderLevel"}
        if not data or set(data) - allowed:
            raise ApiError(400, "Provide one or more supported product fields.")
        mapping = {
            "name": ("name", lambda value: validate_text(value, "Product name")),
            "sku": ("sku", lambda value: validate_text(value, "SKU", 40).upper()),
            "category": ("category", lambda value: validate_text(value, "Category", 60)),
            "priceCents": ("price_cents", lambda value: validate_nonnegative_int(value, "Price")),
            "stock": ("stock", lambda value: validate_nonnegative_int(value, "Stock")),
            "reorderLevel": ("reorder_level", lambda value: validate_nonnegative_int(value, "Reorder level")),
        }
        updates = [(mapping[key][0], mapping[key][1](value)) for key, value in data.items()]
        assignments = ", ".join(f"{column} = ?" for column, _ in updates)
        values = [value for _, value in updates]
        with closing(connect()) as db:
            cursor = db.execute(
                f"UPDATE products SET {assignments} WHERE id = ?", (*values, product_id)
            )
            if cursor.rowcount == 0:
                raise ApiError(404, "Product not found.")
            row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            return self.send_json(200, product_dict(row))

    def create_order(self, data):
        customer = validate_text(data.get("customer"), "Customer", 100)
        raw_items = data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ApiError(400, "Add at least one product to the order.")
        requested: dict[int, int] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                raise ApiError(400, "Each order item must include a product and quantity.")
            product_id = validate_nonnegative_int(item.get("productId"), "Product ID", 1)
            quantity = validate_nonnegative_int(item.get("quantity"), "Quantity", 1)
            requested[product_id] = requested.get(product_id, 0) + quantity

        db = connect()
        try:
            # The write lock makes the read-check-decrement sequence atomic across requests.
            db.execute("BEGIN IMMEDIATE")
            order_items = []
            total_cents = 0
            for product_id, quantity in requested.items():
                product = db.execute(
                    "SELECT * FROM products WHERE id = ?", (product_id,)
                ).fetchone()
                if product is None:
                    raise ApiError(404, f"Product {product_id} was not found.")
                if product["stock"] < quantity:
                    raise ApiError(
                        409,
                        f"Only {product['stock']} of {product['name']} are available.",
                    )
                total_cents += product["price_cents"] * quantity
                order_items.append((product, quantity))

            created_at = now_iso()
            cursor = db.execute(
                "INSERT INTO orders(customer, status, total_cents, created_at) "
                "VALUES (?, 'placed', ?, ?)",
                (customer, total_cents, created_at),
            )
            order_id = cursor.lastrowid
            for product, quantity in order_items:
                updated = db.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (quantity, product["id"], quantity),
                )
                if updated.rowcount != 1:
                    raise ApiError(409, f"Stock changed for {product['name']}. Please try again.")
                db.execute(
                    "INSERT INTO order_items(order_id, product_id, product_name, quantity, unit_price_cents) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (order_id, product["id"], product["name"], quantity, product["price_cents"]),
                )
            db.commit()
            return self.send_json(201, order_rows(db)[0])
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def cancel_order(self, order_id: int):
        db = connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if order is None:
                raise ApiError(404, "Order not found.")
            if order["status"] != "placed":
                raise ApiError(409, "This order has already been cancelled.")
            items = db.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,)
            ).fetchall()
            for item in items:
                db.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )
            db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
            db.commit()
            return self.send_json(200, order_rows(db)[0])
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def main():
    initialize_database()
    host = os.environ.get("SHELFWISE_HOST", "127.0.0.1")
    port = int(os.environ.get("SHELFWISE_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    print(f"Shelfwise is ready at http://{host}:{port}")
    print(f"SQLite database: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Shelfwise...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
