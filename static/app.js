const formEl = document.querySelector("#match-form");
const queryEl = document.querySelector("#query");
const resultsEl = document.querySelector("#results");
const statusEl = document.querySelector("#status");
const customerSearchEl = document.querySelector("#customer-search");
const customerOptionsEl = document.querySelector("#customer-options");
const selectedCustomerEl = document.querySelector("#selected-customer");
const clearCustomerEl = document.querySelector("#clear-customer");
const sampleQueryEl = document.querySelector("#sample-query");
const historyPillEl = document.querySelector("#history-pill");

let customers = [];
let selectedCustomer = null;

const samples = [
  "M8 flat washer",
  "SHCS 7/16 x 2-1/2",
  "1/4-20 x 3/4 hex cap screw zinc",
  "M8 x 50mm BHCS",
  "brass hex nut 1/2-13",
  "the same washers as last time",
];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function setStatus(message, tone = "") {
  statusEl.textContent = message;
  statusEl.className = `status ${tone}`.trim();
}

function renderCustomers(filter = "") {
  const needle = filter.trim().toLowerCase();
  const visible = customers
    .filter((customer) => {
      const text = `${customer.customer_id} ${customer.customer_name}`.toLowerCase();
      return !needle || text.includes(needle);
    })
    .slice(0, 8);

  customerOptionsEl.innerHTML = visible.map((customer) => `
    <button
      type="button"
      class="option"
      data-id="${escapeHtml(customer.customer_id)}"
      role="option"
    >
      <strong>${escapeHtml(customer.customer_id)}</strong>
      <span>${escapeHtml(customer.customer_name)}</span>
      <small>${customer.order_count} orders</small>
    </button>
  `).join("");
  customerOptionsEl.classList.toggle("open", document.activeElement === customerSearchEl && visible.length > 0);
  customerSearchEl.setAttribute("aria-expanded", customerOptionsEl.classList.contains("open") ? "true" : "false");
}

function selectCustomer(customer) {
  selectedCustomer = customer;
  customerSearchEl.value = `${customer.customer_id} · ${customer.customer_name}`;
  selectedCustomerEl.textContent = `Using ${customer.customer_id}: ${customer.customer_name} (${customer.order_count} prior orders).`;
  customerOptionsEl.classList.remove("open");
  customerSearchEl.setAttribute("aria-expanded", "false");
}

function clearCustomer() {
  selectedCustomer = null;
  customerSearchEl.value = "";
  selectedCustomerEl.textContent = "No customer selected. Results use description only.";
  historyPillEl.textContent = "No history boost";
  renderCustomers("");
}

function renderMatches(payload) {
  historyPillEl.textContent = payload.customer
    ? `${Math.round(payload.history_weight * 100)}% history boost`
    : "No history boost";

  resultsEl.innerHTML = payload.matches.map((match, index) => `
    <article class="match-card">
      <div class="match-rank">${index + 1}</div>
      <div class="match-main">
        <div class="match-title">
          <h3>${escapeHtml(match.description)}</h3>
          <span class="confidence">${match.confidence}%</span>
        </div>
        <dl>
          <div><dt>Catalog ID</dt><dd>${escapeHtml(match.catalog_id)}</dd></div>
          <div><dt>SKU</dt><dd>${escapeHtml(match.sku)}</dd></div>
        </dl>
        <div class="reason-list">
          ${match.reasons.map((reason) => `<span>${escapeHtml(reason)}</span>`).join("")}
        </div>
      </div>
    </article>
  `).join("");

  setStatus(
    payload.customer
      ? `Personalized for ${payload.customer.customer_id}.`
      : "Matched using the product description only.",
    "ok",
  );
}

async function loadCustomers() {
  const response = await fetch("/api/customers");
  customers = await response.json();
  renderCustomers("");
}

async function submitMatch() {
  const query = queryEl.value.trim();
  if (!query) {
    setStatus("Type a product description first.", "warn");
    queryEl.focus();
    return;
  }

  formEl.querySelector("button[type='submit']").disabled = true;
  setStatus("Searching catalog...");
  resultsEl.innerHTML = "";

  try {
    const response = await fetch("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        customer_id: selectedCustomer ? selectedCustomer.customer_id : null,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Match failed.");
    renderMatches(payload);
  } catch (error) {
    setStatus(error.message, "warn");
  } finally {
    formEl.querySelector("button[type='submit']").disabled = false;
  }
}

customerSearchEl.addEventListener("input", () => {
  selectedCustomer = null;
  selectedCustomerEl.textContent = "Choose a customer to personalize results.";
  renderCustomers(customerSearchEl.value);
});

customerSearchEl.addEventListener("focus", () => renderCustomers(customerSearchEl.value));

customerOptionsEl.addEventListener("mousedown", (event) => {
  const option = event.target.closest(".option");
  if (!option) return;
  const customer = customers.find((item) => item.customer_id === option.dataset.id);
  if (customer) selectCustomer(customer);
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".combo")) {
    customerOptionsEl.classList.remove("open");
    customerSearchEl.setAttribute("aria-expanded", "false");
  }
});

clearCustomerEl.addEventListener("click", clearCustomer);

sampleQueryEl.addEventListener("click", () => {
  const sample = samples[Math.floor(Math.random() * samples.length)];
  queryEl.value = sample;
  queryEl.focus();
});

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMatch();
});

loadCustomers().catch(() => setStatus("Could not load customers.", "warn"));
