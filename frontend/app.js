const state = { products: [], orders: [], dashboard: null, searchTimer: null };
const currency = cents => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
const dateLabel = value => new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(new Date(value));
const esc = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const iconFor = name => ({ Mug: "☕", Bag: "▱", Plant: "♧", Notebook: "▤", Apron: "◈" }[name] || ({ "Home & Living": "⌂", Accessories: "◒", Stationery: "▤", Kitchen: "◈" }[name] || "◇"));
let toastTimer;

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function showToast(message, isError = false) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function setView(view) {
  document.querySelectorAll(".page-content").forEach(section => { section.hidden = section.id !== `view-${view}`; });
  document.querySelectorAll(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.view === view));
  const label = view === "dashboard" ? "Overview" : view[0].toUpperCase() + view.slice(1);
  document.querySelector("#breadcrumb-current").textContent = label;
  document.title = `${label} | Shelfwise`;
  history.replaceState(null, "", `#${view}`);
  if (view === "inventory") loadProducts();
  if (view === "orders") loadOrders();
}

function statusPill(status) {
  return `<span class="status-pill ${status === "cancelled" ? "cancelled" : ""}">${esc(status)}</span>`;
}

function renderOrderRows(orders, target) {
  const body = document.querySelector(target);
  body.innerHTML = orders.map(order => `<tr>
    <td class="order-id">${esc(order.orderNumber)}</td><td class="customer-cell">${esc(order.customer)}</td>
    <td class="muted-cell">${order.itemCount} ${order.itemCount === 1 ? "item" : "items"}</td>
    <td class="muted-cell">${dateLabel(order.createdAt)}</td><td class="amount-cell">${currency(order.totalCents)}</td>
    <td>${statusPill(order.status)}</td>${target === "#orders-body" ? `<td>${order.status === "placed" ? `<button class="mini-action cancel" data-cancel-order="${order.id}">Cancel</button>` : ""}</td>` : ""}
  </tr>`).join("");
}

async function loadDashboard() {
  const dashboard = await api("/api/dashboard");
  state.dashboard = dashboard;
  document.querySelector("#metric-sales").textContent = currency(dashboard.salesCents);
  document.querySelector("#metric-orders").textContent = dashboard.orderCount;
  document.querySelector("#metric-products").textContent = dashboard.productCount;
  document.querySelector("#metric-low-stock").textContent = dashboard.lowStockCount;
  renderOrderRows(dashboard.recentOrders, "#recent-orders-body");
  document.querySelector("#recent-orders-empty").hidden = dashboard.recentOrders.length !== 0;
  document.querySelector("#low-stock-empty").hidden = dashboard.lowStockProducts.length !== 0;
  document.querySelector("#low-stock-list").innerHTML = dashboard.lowStockProducts.map(product => {
    const swatch = product.category === "Kitchen" ? "peach" : product.category === "Stationery" ? "blue" : product.category === "Accessories" ? "yellow" : "green";
    return `<div class="stock-row"><span class="product-swatch ${swatch}">${iconFor(product.name.split(" ")[0])}</span><span class="stock-copy"><strong>${esc(product.name)}</strong><small>${esc(product.sku)} · Reorder at ${product.reorderLevel}</small></span><span class="stock-count">${product.stock} left</span></div>`;
  }).join("");
}

async function loadProducts(search = "") {
  state.products = await api(`/api/products?search=${encodeURIComponent(search)}`);
  document.querySelector("#inventory-count").textContent = state.products.length;
  document.querySelector("#inventory-empty").hidden = state.products.length !== 0;
  document.querySelector("#products-body").innerHTML = state.products.map(product => {
    const low = product.stock <= product.reorderLevel;
    const swatch = product.category === "Kitchen" ? "peach" : product.category === "Stationery" ? "blue" : product.category === "Accessories" ? "yellow" : "green";
    return `<tr><td><span class="item-name"><span class="product-swatch ${swatch}">${iconFor(product.name.split(" ")[0])}</span><span><strong>${esc(product.name)}</strong><small>${esc(product.category)}</small></span></span></td>
      <td class="muted-cell">${esc(product.sku)}</td><td class="muted-cell">${esc(product.category)}</td><td class="amount-cell">${currency(product.priceCents)}</td>
      <td><input class="stock-input" type="number" min="0" step="1" value="${product.stock}" aria-label="Stock for ${esc(product.name)}" data-stock-input="${product.id}" /></td>
      <td>${low ? `<span class="status-pill cancelled">Low stock</span>` : `<span class="status-pill">In stock</span>`}</td>
      <td><button class="mini-action" data-save-stock="${product.id}">Save</button></td></tr>`;
  }).join("");
}

async function loadOrders() {
  state.orders = await api("/api/orders");
  document.querySelector("#orders-count").textContent = state.orders.length;
  document.querySelector("#orders-empty").hidden = state.orders.length !== 0;
  renderOrderRows(state.orders, "#orders-body");
}

function openProductDialog() {
  document.querySelector("#product-form").reset();
  document.querySelector('#product-form [name="reorderLevel"]').value = 5;
  document.querySelector("#product-dialog").showModal();
}

function updateOrderTotal() {
  const total = [...document.querySelectorAll(".line-row")].reduce((sum, row) => {
    const id = Number(row.querySelector("select").value);
    const quantity = Math.max(0, Number(row.querySelector("input").value || 0));
    const product = state.products.find(item => item.id === id);
    return sum + (product ? product.priceCents * quantity : 0);
  }, 0);
  document.querySelector("#order-total").textContent = currency(total);
}

function addOrderLine() {
  if (!state.products.length) {
    showToast("Add a product to your inventory before creating an order.", true);
    return;
  }
  const row = document.createElement("div");
  row.className = "line-row";
  row.innerHTML = `<select aria-label="Product">${state.products.map(product => `<option value="${product.id}" ${product.stock === 0 ? "disabled" : ""}>${esc(product.name)} · ${product.stock} available</option>`).join("")}</select><input type="number" min="1" step="1" value="1" aria-label="Quantity" /><button type="button" class="remove-line" aria-label="Remove item">×</button>`;
  row.querySelector("select").addEventListener("change", updateOrderTotal);
  row.querySelector("input").addEventListener("input", updateOrderTotal);
  row.querySelector(".remove-line").addEventListener("click", () => { row.remove(); updateOrderTotal(); });
  document.querySelector("#order-lines").append(row);
  updateOrderTotal();
}

async function openOrderDialog() {
  try {
    state.products = await api("/api/products");
    document.querySelector("#order-form").reset();
    document.querySelector("#order-lines").innerHTML = "";
    addOrderLine();
    document.querySelector("#order-dialog").showModal();
  } catch (error) { showToast(error.message, true); }
}

document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => setView(button.dataset.view)));
document.querySelectorAll('[data-action="new-product"]').forEach(button => button.addEventListener("click", openProductDialog));
document.querySelectorAll('[data-action="new-order"]').forEach(button => button.addEventListener("click", openOrderDialog));
document.querySelectorAll("[data-close]").forEach(button => button.addEventListener("click", () => document.querySelector(`#${button.dataset.close}`).close()));
document.querySelectorAll("dialog").forEach(dialog => dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); }));
document.querySelector("#add-order-line").addEventListener("click", addOrderLine);

document.querySelector("#product-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const amount = Math.round(Number(form.get("price")) * 100);
  try {
    await api("/api/products", { method: "POST", body: JSON.stringify({ name: form.get("name"), sku: form.get("sku"), category: form.get("category") || "General", priceCents: amount, stock: Number(form.get("stock")), reorderLevel: Number(form.get("reorderLevel")) }) });
    document.querySelector("#product-dialog").close();
    showToast("Product added to your inventory.");
    await Promise.all([loadDashboard(), loadProducts(document.querySelector("#product-search").value)]);
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#order-form").addEventListener("submit", async event => {
  event.preventDefault();
  const customer = new FormData(event.currentTarget).get("customer");
  const items = [...document.querySelectorAll(".line-row")].map(row => ({ productId: Number(row.querySelector("select").value), quantity: Number(row.querySelector("input").value) }));
  if (!items.length || items.some(item => !Number.isInteger(item.quantity) || item.quantity < 1)) { showToast("Each order quantity must be at least 1.", true); return; }
  try {
    const order = await api("/api/orders", { method: "POST", body: JSON.stringify({ customer, items }) });
    document.querySelector("#order-dialog").close();
    showToast(`${order.orderNumber} placed. Stock has been updated.`);
    await Promise.all([loadDashboard(), loadProducts(document.querySelector("#product-search").value), loadOrders()]);
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#product-search").addEventListener("input", event => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(() => loadProducts(event.target.value).catch(error => showToast(error.message, true)), 180);
});

document.querySelector("#products-body").addEventListener("click", async event => {
  const button = event.target.closest("[data-save-stock]");
  if (!button) return;
  const id = Number(button.dataset.saveStock);
  const stock = Number(document.querySelector(`[data-stock-input="${id}"]`).value);
  try {
    await api(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify({ stock }) });
    showToast("Stock level updated.");
    await Promise.all([loadProducts(document.querySelector("#product-search").value), loadDashboard()]);
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#orders-body").addEventListener("click", async event => {
  const button = event.target.closest("[data-cancel-order]");
  if (!button) return;
  try {
    await api(`/api/orders/${button.dataset.cancelOrder}/cancel`, { method: "POST", body: "{}" });
    showToast("Order cancelled and items returned to stock.");
    await Promise.all([loadOrders(), loadDashboard(), loadProducts(document.querySelector("#product-search").value)]);
  } catch (error) { showToast(error.message, true); }
});

const formattedToday = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric" }).format(new Date());
document.querySelector("#today-label").textContent = formattedToday;
const initialView = ["dashboard", "inventory", "orders"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard";
setView(initialView);
loadDashboard().catch(error => showToast(error.message, true));
