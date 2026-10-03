const $ = id => document.getElementById(id);

const FIELD_DEFS = {
  password: [["Username", "text", "username"], ["Password", "password", "password"], ["URL", "url", "url"]],
  note: [["Content", "textarea", "content"]],
  totp: [["Secret (base32)", "text", "secret"], ["Issuer", "text", "issuer"], ["Account name", "text", "account"]]
};

const TYPE_LABEL = { password: "Password", note: "Note", totp: "TOTP" };
const API_BASE = '/api';

let currentUser = null;
let currentKey = null;
let editingId = null;
let totpTimer = null;
let authToken = localStorage.getItem('pm_token') || null;
let csrfToken = null;

const enc = new TextEncoder();
const dec = new TextDecoder();

// ---------------- API helper ----------------
async function api(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = 'Bearer ' + authToken;
  if (csrfToken && method !== 'GET') headers['X-CSRF-Token'] = csrfToken;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(API_BASE + path, opts);
  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || ('Request failed: ' + res.status));
  return data;
}

// ---------------- storage ----------------
function getUsers() { return JSON.parse(localStorage.getItem("pm_users") || "{}"); }
function setUsers(u) { localStorage.setItem("pm_users", JSON.stringify(u)); }
function dataKey(u) { return "pm_data_" + u; }
function getData() { return JSON.parse(localStorage.getItem(dataKey(currentUser)) || '{"vaults":[]}'); }
function setData(d) { localStorage.setItem(dataKey(currentUser), JSON.stringify(d)); }

// ---------------- crypto helpers ----------------
function b64(bytes) { return btoa(String.fromCharCode.apply(null, bytes)); }
function unb64(s) { return Uint8Array.from(atob(s), c => c.charCodeAt(0)); }

async function sha256b64(s) {
  return b64(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(s))));
}

async function deriveKey(password, salt) {
  const base = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 150000, hash: "SHA-256" },
    base,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

async function encryptJSON(key, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, enc.encode(JSON.stringify(obj))));
  return b64(ct) + "." + b64(iv);
}

async function decryptJSON(key, str) {
  const [ct, iv] = str.split(".");
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(iv) }, key, unb64(ct));
  return JSON.parse(dec.decode(pt));
}

// ---------------- TOTP (RFC 6238) ----------------
const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function base32decode(s) {
  let bits = 0, val = 0;
  const out = [];
  for (const ch of s.replace(/\s+/g, "").toUpperCase()) {
    const n = BASE32.indexOf(ch);
    if (n < 0) continue;
    val = (val << 5) | n;
    bits += 5;
    if (bits >= 8) { out.push((val >>> (bits - 8)) & 0xff); bits -= 8; }
  }
  return new Uint8Array(out);
}

async function totpCode(secret, period = 30) {
  const counter = Math.floor(Date.now() / 1000 / period);
  const buf = new ArrayBuffer(8);
  new DataView(buf).setUint32(4, counter >>> 0, false);
  const key = await crypto.subtle.importKey("raw", base32decode(secret), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const h = new Uint8Array(await crypto.subtle.sign("HMAC", key, buf));
  const off = h[h.length - 1] & 0x0f;
  const code = ((h[off] & 0x7f) << 24) | (h[off + 1] << 16) | (h[off + 2] << 8) | h[off + 3];
  return {
    value: String(code % 1000000).padStart(6, "0"),
    expires: (counter + 1) * period - Math.floor(Date.now() / 1000)
  };
}

// ---------------- view switching ----------------
function showAuth() {
  $("app-view").classList.add("hidden");
  $("auth-view").classList.remove("hidden");
  $("auth-form").reset();
  setTab("login");
}

function showApp() {
  $("auth-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  loadVaults();
}

// ---------------- auth ----------------
function isRegister() { return $("tab-register").classList.contains("active"); }

function setTab(mode) {
  const reg = mode === "register";
  $("tab-login").classList.toggle("active", !reg);
  $("tab-register").classList.toggle("active", reg);
  $("email-field").classList.toggle("hidden", !reg);
  $("auth-submit").textContent = reg ? "Register" : "Login";
  $("auth-password").autocomplete = reg ? "new-password" : "current-password";
  $("auth-error").textContent = "";
}

async function submitAuth(e) {
  e.preventDefault();
  $("auth-error").textContent = "";
  const username = $("auth-username").value.trim();
  const password = $("auth-password").value;
  if (!username || !password) { $("auth-error").textContent = "Fill in all fields."; return; }

  try {
    let data;
    if (isRegister()) {
      const email = $("auth-email").value.trim();
      if (!email) { $("auth-error").textContent = "Email is required."; return; }
      data = await api('POST', '/auth/register', { username, email, password });
    } else {
      data = await api('POST', '/auth/login', { username, password });
    }

    authToken = data.token;
    csrfToken = data.csrf_token;
    localStorage.setItem('pm_token', authToken);
    currentUser = data.user.username;

    const all = getUsers();
    if (!all[currentUser]) {
      const saltB64 = b64(crypto.getRandomValues(new Uint8Array(16)));
      all[currentUser] = { email: data.user.email, salt: saltB64, verifier: await sha256b64(password), createdAt: Date.now() };
      setUsers(all);
    }
    currentKey = await deriveKey(password, unb64(all[currentUser].salt));

    showApp();
  } catch (err) {
    $("auth-error").textContent = err.message;
  }
}

async function logout() {
  try { await api('POST', '/auth/logout'); } catch {}
  authToken = null;
  csrfToken = null;
  localStorage.removeItem('pm_token');
  currentUser = null;
  currentKey = null;
  showAuth();
}

// ---------------- vaults & items (API-backed) ----------------
function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
function fmt(ts) { return new Date(ts).toLocaleString(); }
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadVaults() {
  try {
    const data = await api('GET', '/vaults');
    const sel = $("vault-select");
    sel.innerHTML = "";
    for (const v of data.vaults) {
      const o = document.createElement("option");
      o.value = v.VaultID;
      o.textContent = v.VaultName;
      sel.appendChild(o);
    }
    if (!data.vaults.length) {
      $("item-list").innerHTML = '<p class="empty">No vaults yet. Create one.</p>';
      return;
    }
    loadItems();
  } catch (err) {
    $("item-list").innerHTML = '<p class="empty">Error: ' + esc(err.message) + '</p>';
  }
}

async function loadItems() {
  const vaultId = $("vault-select").value;
  if (!vaultId) return;
  try {
    const data = await api('GET', '/vaults/' + vaultId + '/items');
    renderItems(data.items);
  } catch (err) {
    $("item-list").innerHTML = '<p class="empty">Error: ' + esc(err.message) + '</p>';
  }
}

function renderItems(items) {
  const list = $("item-list");
  list.innerHTML = "";
  if (!items.length) { list.innerHTML = '<p class="empty">No items yet. Add one.</p>'; return; }

  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    const typeLabel = TYPE_LABEL[item.ItemType?.toLowerCase()] || item.ItemType;
    card.innerHTML =
      '<div class="item-main">' +
      `<span class="badge ${item.ItemType?.toLowerCase()}">${typeLabel}</span>` +
      `<span class="item-title">${esc(item.Title)}</span>` +
      `<span class="item-meta">${fmt(item.CreatedAt)}</span>` +
      "</div>" +
      '<div class="item-actions">' +
      `<button data-edit="${item.ItemID}" class="ghost small">Edit</button> ` +
      `<button data-del="${item.ItemID}" class="ghost small danger">Delete</button>` +
      "</div>";
    card.addEventListener("click", e => {
      if (e.target.dataset.edit) { openItemForm(item); return; }
      if (e.target.dataset.del) { deleteItem(item.ItemID); return; }
      openDetail(item);
    });
    list.appendChild(card);
  }
}

async function newVault() {
  const name = prompt("Vault name");
  if (!name || !name.trim()) return;
  try {
    await api('POST', '/vaults', { name: name.trim() });
    loadVaults();
  } catch (err) { alert(err.message); }
}

async function deleteItem(id) {
  if (!confirm("Delete this item?")) return;
  try {
    await api('DELETE', '/items/' + id);
    loadItems();
  } catch (err) { alert(err.message); }
}

// ---------------- item form modal ----------------
async function openItemForm(item) {
  editingId = item ? item.ItemID : null;
  $("item-modal-title").textContent = item ? "Edit item" : "New item";
  $("item-error").textContent = "";
  $("item-title").value = item ? item.Title : "";
  $("item-type").value = item ? item.ItemType?.toLowerCase() : "password";
  $("item-type").disabled = !!item;

  let existing = null;
  if (item && item.typeData) {
    existing = item.typeData;
  }
  renderItemFields(existing);
  $("item-modal").classList.remove("hidden");
}

function renderItemFields(existing) {
  const type = $("item-type").value;
  const box = $("item-fields");
  box.innerHTML = "";
  for (const [labelText, inputType, name] of FIELD_DEFS[type]) {
    const wrap = document.createElement("div");
    wrap.className = "field";
    const label = document.createElement("label");
    label.textContent = labelText;
    label.htmlFor = "f_" + name;
    const input = document.createElement(inputType === "textarea" ? "textarea" : "input");
    input.id = "f_" + name;
    input.name = name;
    if (inputType !== "textarea") input.type = inputType;
    if (inputType === "password" || name === "secret") input.autocomplete = "off";
    if (existing && existing[name] != null) input.value = existing[name];
    wrap.append(label, input);
    box.appendChild(wrap);
  }
}

async function saveItem() {
  $("item-error").textContent = "";
  const type = $("item-type").value;
  const title = $("item-title").value.trim();
  if (!title) { $("item-error").textContent = "Title is required."; return; }

  const fields = {};
  for (const [, , name] of FIELD_DEFS[type]) {
    const el = $("f_" + name);
    fields[name] = el ? el.value.trim() : "";
  }

  const vaultId = $("vault-select").value;
  try {
    if (editingId) {
      await api('PUT', '/items/' + editingId, { title, ...fields });
    } else {
      await api('POST', '/vaults/' + vaultId + '/items', { title, type: type.toUpperCase(), ...fields });
    }
    closeModal("item-modal");
    loadItems();
  } catch (err) {
    $("item-error").textContent = err.message;
  }
}

// ---------------- detail modal ----------------
async function openDetail(item) {
  const body = $("detail-body");
  body.innerHTML = "";
  $("detail-title").textContent = item.Title;

  const fields = item.typeData || {};

  if (item.ItemType === "SECURE_NOTE") {
    const p = document.createElement("p");
    p.className = "note";
    p.textContent = fields.content || fields.ContentEnc || "";
    body.appendChild(p);
  }

  if (item.ItemType === "TOTP") {
    const box = document.createElement("div");
    box.className = "totp-code";
    body.appendChild(box);
    const secret = fields.secret || fields.SecretEnc || "";
    const refresh = async () => {
      const t = await totpCode(secret);
      box.innerHTML = `<span class="big">${t.value}</span> <span class="exp">expires in ${t.expires}s</span>`;
    };
    refresh();
    if (totpTimer) clearInterval(totpTimer);
    totpTimer = setInterval(refresh, 1000);
  }

  const rows = [];
  if (item.ItemType === "PASSWORD") {
    rows.push(["Username", fields.username || fields.UsernameEnc, false]);
    rows.push(["Password", fields.password || fields.PasswordEnc, true]);
    rows.push(["URL", fields.url || fields.UrlEnc, false]);
  } else if (item.ItemType === "TOTP") {
    rows.push(["Secret", fields.secret || fields.SecretEnc, true]);
    rows.push(["Issuer", fields.issuer || fields.Issuer, false]);
    rows.push(["Account", fields.account || fields.AccountName, false]);
  }

  for (const [labelText, val, secret] of rows) {
    const row = document.createElement("div");
    row.className = "field row";
    row.innerHTML = `<label>${labelText}</label><input type="text" value="${esc(val)}" readonly><button class="ghost small copy" style="flex:0 0 auto">Copy</button>`;
    row.querySelector(".copy").addEventListener("click", async e => {
      await copyText(val);
      e.currentTarget.textContent = "Copied";
      setTimeout(() => { e.currentTarget.textContent = "Copy"; }, 1200);
    });
    body.appendChild(row);
  }

  $("detail-modal").classList.remove("hidden");
}

function closeDetail() {
  if (totpTimer) { clearInterval(totpTimer); totpTimer = null; }
  $("detail-modal").classList.add("hidden");
}

function closeModal(id) {
  $(id).classList.add("hidden");
  if (id === "item-modal") {
    editingId = null;
    $("item-type").disabled = false;
    $("item-error").textContent = "";
  }
}

// ---------------- misc ----------------
async function copyText(t) {
  try { await navigator.clipboard.writeText(t); }
  catch { alert("Clipboard unavailable (needs a secure context, e.g. localhost)."); }
}

// ---------------- wire up ----------------
$("auth-form").addEventListener("submit", submitAuth);
$("tab-login").addEventListener("click", () => setTab("login"));
$("tab-register").addEventListener("click", () => setTab("register"));
$("logout").addEventListener("click", logout);
$("add-item").addEventListener("click", () => openItemForm(null));
$("new-vault").addEventListener("click", newVault);
$("item-type").addEventListener("change", () => renderItemFields(null));
$("item-save").addEventListener("click", saveItem);
$("item-cancel").addEventListener("click", () => closeModal("item-modal"));
$("detail-close").addEventListener("click", closeDetail);
$("vault-select").addEventListener("change", loadItems);

showAuth();
