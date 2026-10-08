from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "Shelfwise_Project_Guide.pdf"

INK = colors.HexColor("#222A38")
MUTED = colors.HexColor("#778194")
PURPLE = colors.HexColor("#635BDA")
LIGHT_PURPLE = colors.HexColor("#F1EFFF")
PALE = colors.HexColor("#F6F7FA")
LINE = colors.HexColor("#E6E9EF")
GREEN = colors.HexColor("#168267")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=12, textColor=PURPLE, tracking=1.4, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=34, leading=39, textColor=INK, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=14, leading=21, textColor=MUTED, spaceAfter=18))
styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=21, leading=26, textColor=INK, spaceBefore=2, spaceAfter=9))
styles.add(ParagraphStyle(name="SectionIntro", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=15, textColor=MUTED, spaceAfter=15))
styles.add(ParagraphStyle(name="Subhead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=INK, spaceBefore=8, spaceAfter=6))
styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=14, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="BodyTiny", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=11.5, textColor=INK))
styles.add(ParagraphStyle(name="MutedSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED))
styles.add(ParagraphStyle(name="BulletSmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13.5, leftIndent=12, firstLineIndent=-8, bulletIndent=0, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="TableHead", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=WHITE))
styles.add(ParagraphStyle(name="TableBody", parent=styles["Normal"], fontName="Helvetica", fontSize=7.7, leading=11, textColor=INK))
styles["Code"].fontName = "Courier"
styles["Code"].fontSize = 8.5
styles["Code"].leading = 13
styles["Code"].textColor = INK
styles["Code"].backColor = PALE
styles["Code"].borderColor = LINE
styles["Code"].borderWidth = 0.5
styles["Code"].borderPadding = 10
styles["Code"].spaceBefore = 5
styles["Code"].spaceAfter = 8
styles.add(ParagraphStyle(name="CalloutTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=PURPLE, spaceAfter=3))
styles.add(ParagraphStyle(name="CalloutBody", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=13, textColor=INK))
styles.add(ParagraphStyle(name="CenterSmall", parent=styles["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER))


def P(text, style="BodySmall"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph("• " + text, styles["BulletSmall"])


def table(rows, widths, header=True, padd=7):
    result = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padd),
        ("RIGHTPADDING", (0, 0), (-1, -1), padd),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), INK), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE])]
    else:
        commands += [("BACKGROUND", (0, 0), (-1, -1), PALE)]
    result.setStyle(TableStyle(commands))
    return result


def callout(title, body, color=LIGHT_PURPLE):
    box = Table([[P(title, "CalloutTitle")], [P(body, "CalloutBody")]], colWidths=[6.75 * inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 3, PURPLE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
    ]))
    return box


class ArchitectureDiagram(Flowable):
    def __init__(self, width=6.8 * inch, height=1.45 * inch):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        boxes = [
            (0, 0.34 * inch, 1.65 * inch, 0.78 * inch, "Browser UI", "HTML + CSS + JS", LIGHT_PURPLE, PURPLE),
            (2.55 * inch, 0.34 * inch, 1.75 * inch, 0.78 * inch, "HTTP API", "Python stdlib", colors.HexColor("#EAF3FF"), colors.HexColor("#3D76BD")),
            (5.1 * inch, 0.34 * inch, 1.65 * inch, 0.78 * inch, "Database", "SQLite", colors.HexColor("#EAF7F1"), GREEN),
        ]
        for x, y, w, h, title, sub, fill, accent in boxes:
            c.setFillColor(fill)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
            c.setFillColor(accent)
            c.roundRect(x + 0.12 * inch, y + 0.13 * inch, 3, h - 0.26 * inch, 1.5, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 0.27 * inch, y + 0.47 * inch, title)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(x + 0.27 * inch, y + 0.26 * inch, sub)
        c.setStrokeColor(colors.HexColor("#AEB5C3"))
        c.setLineWidth(1.5)
        for start, end in [(1.72 * inch, 2.47 * inch), (4.37 * inch, 5.02 * inch)]:
            y = 0.73 * inch
            c.line(start, y, end, y)
            c.line(end - 5, y + 4, end, y)
            c.line(end - 5, y - 4, end, y)


def draw_page(canvas, document):
    canvas.saveState()
    width, height = letter
    if document.page == 1:
        canvas.setFillColor(INK)
        canvas.rect(0, height - 0.16 * inch, width, 0.16 * inch, fill=1, stroke=0)
    else:
        canvas.setStrokeColor(LINE)
        canvas.line(document.leftMargin, height - 0.45 * inch, width - document.rightMargin, height - 0.45 * inch)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(PURPLE)
        canvas.drawString(document.leftMargin, height - 0.36 * inch, "SHELFWISE  /  PROJECT GUIDE")
    canvas.setStrokeColor(LINE)
    canvas.line(document.leftMargin, 0.47 * inch, width - document.rightMargin, 0.47 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 0.29 * inch, "Shelfwise - Shop inventory and orders")
    canvas.drawRightString(width - document.rightMargin, 0.29 * inch, f"{document.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        rightMargin=0.72 * inch, leftMargin=0.72 * inch,
        topMargin=0.72 * inch, bottomMargin=0.68 * inch,
        title="Shelfwise - Complete Project Guide",
        author="Shelfwise Project Notes",
        subject="Product guide, architecture, API, and interview walkthrough",
    )
    story = []

    # 1. Cover
    story += [Spacer(1, 0.62 * inch), P("A FULL-STACK LEARNING PROJECT", "CoverEyebrow"), P("Shelfwise", "CoverTitle"), P("A small-shop inventory and order manager built to keep stock accurate and make daily shop work easier.", "CoverSubtitle"), HRFlowable(width="100%", thickness=1.2, color=LINE, spaceBefore=5, spaceAfter=18)]
    story += [ArchitectureDiagram(), P("How the parts work together", "CenterSmall"), Spacer(1, 0.22 * inch)]
    facts = [
        [P("THE PROBLEM", "TableHead"), P("THE CORE RULE", "TableHead"), P("THE STACK", "TableHead")],
        [P("A shop needs a reliable view of products, stock, and sales orders.", "TableBody"), P("An order deducts stock as one transaction, or it is rejected without partial changes.", "TableBody"), P("Python standard library, SQLite, and a responsive browser UI.", "TableBody")],
    ]
    story += [table(facts, [2.25 * inch] * 3), Spacer(1, 0.23 * inch), callout("What this guide covers", "The product flow, folder structure, data model, stock-safety transaction, API endpoints, local setup, and a concise interview walkthrough."), Spacer(1, 0.16 * inch), P("Project status: local starter implementation. GitHub publishing is intentionally left for later.", "MutedSmall"), PageBreak()]

    # 2. Product tour
    story += [P("01  /  PRODUCT TOUR", "CoverEyebrow"), P("What Shelfwise does", "SectionTitle"), P("Shelfwise gives a small shop one place to check inventory and record orders. The screens are deliberately simple so the business rules are easy to see.", "SectionIntro")]
    feature_rows = [
        [P("SCREEN", "TableHead"), P("WHAT YOU CAN DO", "TableHead"), P("WHY IT MATTERS", "TableHead")],
        [P("Overview", "TableBody"), P("See active sales, order count, product count, low-stock items, and recent orders.", "TableBody"), P("A shop owner sees the work that needs attention first.", "TableBody")],
        [P("Inventory", "TableBody"), P("Search products, add an item, update its on-hand stock, and export the complete catalog to CSV.", "TableBody"), P("Stock counts and reorder points stay easy to review in the app or a spreadsheet.", "TableBody")],
        [P("Orders", "TableBody"), P("Create a multi-item order or cancel a placed order.", "TableBody"), P("Order creation deducts stock; cancellation returns it.", "TableBody")],
    ]
    story += [table(feature_rows, [1.05 * inch, 3.0 * inch, 2.7 * inch]), Spacer(1, 0.18 * inch), P("The main user flow", "Subhead")]
    flow = [[P("1. Find an item", "CalloutTitle"), P("2. Place an order", "CalloutTitle"), P("3. Stock updates", "CalloutTitle"), P("4. Review the result", "CalloutTitle")], [P("Search the catalog and check its available units.", "BodyTiny"), P("Choose a customer and one or more products.", "BodyTiny"), P("Stock is deducted only if every requested quantity is available.", "BodyTiny"), P("The dashboard and order history refresh from the API.", "BodyTiny")]]
    story += [table(flow, [1.68 * inch] * 4, header=False), Spacer(1, 0.18 * inch), callout("Try this after starting the app", "Create an order for a product with enough stock. Then place another order for more than the remaining amount. The second request should be rejected, and inventory should remain unchanged."), Spacer(1, 0.17 * inch), P("The starter data uses sample shop products. You can delete the local database file to reset the demo; the next run seeds the sample catalog again.", "MutedSmall"), PageBreak()]

    # 3. Architecture and files
    story += [P("02  /  ARCHITECTURE", "CoverEyebrow"), P("How the code is organized", "SectionTitle"), P("The browser renders the screens and calls a small JSON API. The API validates requests, applies business rules, and persists the result in SQLite.", "SectionIntro"), ArchitectureDiagram(), Spacer(1, 0.1 * inch)]
    files = [
        [P("PATH", "TableHead"), P("RESPONSIBILITY", "TableHead")],
        [P("backend/server.py", "TableBody"), P("HTTP routes, request validation, database schema, sample data, order transactions, and cancellation logic.", "TableBody")],
        [P("frontend/index.html", "TableBody"), P("The dashboard, inventory and order screens, and accessible product/order dialogs.", "TableBody")],
        [P("frontend/styles.css", "TableBody"), P("Visual styles and responsive behavior for laptop and mobile widths.", "TableBody")],
        [P("frontend/app.js", "TableBody"), P("Fetch calls, form events, view navigation, loading data, updating the UI, and safe CSV generation.", "TableBody")],
        [P("data/shelfwise.db", "TableBody"), P("Local SQLite file created when the server starts. It is ignored by Git.", "TableBody")],
    ]
    story += [table(files, [1.75 * inch, 5.0 * inch]), Spacer(1, 0.16 * inch), P("A typical request", "Subhead"), P("The browser sends JSON with fetch(). The Python handler routes the request, checks the fields, and uses SQL statements to read or change data. The server sends JSON back; the browser then updates the visible page. Both ends use JSON, so the browser does not need direct database access.", "BodySmall"), callout("Why the UI and server are separate", "The same API rules apply whether an order comes from this screen, a future mobile app, or another client. Keeping the rule on the server prevents a browser-side check from being bypassed."), PageBreak()]

    # 4. Data and transaction
    story += [P("03  /  DATA AND STOCK SAFETY", "CoverEyebrow"), P("The important backend decision", "SectionTitle"), P("Inventory is shared data. If two requests try to sell the last unit at nearly the same time, a read-then-write sequence without a transaction could oversell it.", "SectionIntro")]
    schema_rows = [
        [P("TABLE", "TableHead"), P("KEY FIELDS", "TableHead"), P("RELATIONSHIP", "TableHead")],
        [P("products", "TableBody"), P("id, name, sku, price_cents, stock, reorder_level", "TableBody"), P("One product can appear in many order_items rows.", "TableBody")],
        [P("orders", "TableBody"), P("id, customer, status, total_cents, created_at", "TableBody"), P("One order owns one or more order_items rows.", "TableBody")],
        [P("order_items", "TableBody"), P("order_id, product_id, product_name, quantity, unit_price_cents", "TableBody"), P("Connects products and orders; stores the name and price at order time.", "TableBody")],
    ]
    story += [table(schema_rows, [1.2 * inch, 2.5 * inch, 3.05 * inch]), Spacer(1, 0.15 * inch), P("Order creation, in sequence", "Subhead")]
    steps = [
        [P("01", "CalloutTitle"), P("Open a write transaction with BEGIN IMMEDIATE so another writer cannot change stock during this order.", "BodyTiny")],
        [P("02", "CalloutTitle"), P("Read each requested product and confirm it exists and has enough stock.", "BodyTiny")],
        [P("03", "CalloutTitle"), P("Create the order, conditionally deduct stock, and add each order line.", "BodyTiny")],
        [P("04", "CalloutTitle"), P("Commit only when every step succeeds. If any step fails, rollback removes all changes.", "BodyTiny")],
    ]
    step_table = Table(steps, colWidths=[0.52 * inch, 6.23 * inch])
    step_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (0, -1), LIGHT_PURPLE), ("BACKGROUND", (1, 0), (1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [step_table, Spacer(1, 0.16 * inch), callout("Why store price and name on the order item?", "The product catalog can change later. An order should still show the item name and price that applied when it was placed, so order_items stores a snapshot.", color=colors.HexColor("#EAF7F1")), Spacer(1, 0.14 * inch), P("Money is stored as whole cents, such as 1899 for $18.99. Integer arithmetic avoids floating-point rounding surprises when calculating totals.", "MutedSmall"), PageBreak()]

    # 5. API and local run
    story += [P("04  /  API AND SETUP", "CoverEyebrow"), P("How to run and explore it", "SectionTitle"), P("Shelfwise has no third-party Python packages. Python starts the web server and serves the frontend files from the same local address.", "SectionIntro"), P("Start the app", "Subhead"), Spacer(1, 0.08 * inch), P("python backend/server.py", "Code"), P("Run the command from the project folder. Open <b>http://127.0.0.1:8000</b>. Stop the server with Ctrl+C. Requires Python 3.10 or newer.", "BodySmall")]
    api_rows = [
        [P("METHOD + PATH", "TableHead"), P("WHAT IT DOES", "TableHead"), P("COMMON RESPONSE", "TableHead")],
        [P("GET /api/dashboard", "TableBody"), P("Returns summary metrics, low-stock products, and recent orders.", "TableBody"), P("200 with dashboard JSON", "TableBody")],
        [P("GET /api/products?search=...", "TableBody"), P("Lists products; optional text search checks product name, SKU, and category.", "TableBody"), P("200 with product array", "TableBody")],
        [P("POST /api/products", "TableBody"), P("Creates a catalog item. Price is supplied as cents.", "TableBody"), P("201, or 409 for duplicate SKU", "TableBody")],
        [P("PATCH /api/products/{id}", "TableBody"), P("Updates supported fields, including the on-hand stock value.", "TableBody"), P("200, or 404 if missing", "TableBody")],
        [P("GET /api/orders", "TableBody"), P("Lists orders with saved item snapshots.", "TableBody"), P("200 with order array", "TableBody")],
        [P("POST /api/orders", "TableBody"), P("Places a multi-product order and deducts stock transactionally.", "TableBody"), P("201, or 409 for insufficient stock", "TableBody")],
        [P("POST /api/orders/{id}/cancel", "TableBody"), P("Cancels a placed order once and returns units to stock.", "TableBody"), P("200, or 409 if already cancelled", "TableBody")],
    ]
    story += [P("API reference", "Subhead"), table(api_rows, [2.12 * inch, 2.92 * inch, 1.71 * inch]), Spacer(1, 0.15 * inch), callout("HTTP status codes", "400 means invalid input; 404 means the requested record does not exist; 409 means a business rule prevents the change, such as a duplicate SKU or insufficient stock."), PageBreak()]

    # 6. Explain it
    story += [P("05  /  INTERVIEW WALKTHROUGH", "CoverEyebrow"), P("How to explain the project", "SectionTitle"), P("A concise story helps an interviewer understand the problem before looking at individual files.", "SectionIntro"), callout("30-second project summary", "I built Shelfwise, a small-shop inventory and order manager. It has a responsive browser UI, a Python JSON API, and SQLite persistence. The core engineering problem is keeping stock correct: each order checks availability and applies every stock deduction in one transaction, so rejected orders do not leave partial changes."), Spacer(1, 0.17 * inch), P("A practical demo sequence", "Subhead")]
    demo_rows = [
        [P("SHOW", "TableHead"), P("SAY", "TableHead")],
        [P("Overview", "TableBody"), P("""The summary is calculated from saved orders and current inventory, not hard-coded labels.""", "TableBody")],
        [P("Inventory search", "TableBody"), P("""A product has a SKU, price, on-hand stock, and reorder point. Search is handled by the API.""", "TableBody")],
        [P("Create order", "TableBody"), P("""The order may have several lines. The server validates all requested quantities before it commits.""", "TableBody")],
        [P("Insufficient stock", "TableBody"), P("""A conflict response leaves the order list and stock unchanged. That rule belongs on the server.""", "TableBody")],
        [P("Cancel order", "TableBody"), P("""A placed order can be cancelled once; the same transaction restores the units.""", "TableBody")],
    ]
    story += [table(demo_rows, [1.35 * inch, 5.4 * inch]), Spacer(1, 0.14 * inch), P("Good follow-up topics", "Subhead"), bullet("Why SQLite is enough for a local demo, and what would change for a multi-user hosted shop."), bullet("Why cents are stored as integers instead of floating-point currency."), bullet("How the transaction protects stock when requests overlap."), bullet("What you would add next: authentication, audit history, automated tests, and backups."), Spacer(1, 0.12 * inch), callout("Current limitations", "This starter has no sign-in, roles, online deployment, automated test suite, or backup process. Describe those as future work, not as features that already exist.", color=colors.HexColor("#FFF4E9")), Spacer(1, 0.13 * inch), P("Keep GitHub for later", "Subhead"), P("The project is saved locally in its own folder. When you are ready to publish it, you can review the files, initialize Git, create a new repository under your account, and push the branch. Nothing in this setup has published it to GitHub.", "BodySmall")]

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(OUTPUT)


if __name__ == "__main__":
    build()
