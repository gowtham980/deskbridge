/* DeskBridge web console helpers */

function toast(message, isError = false) {
  const region = document.getElementById("toast-region");
  if (!region) return;
  const el = document.createElement("div");
  el.className = `toast${isError ? " error" : ""}`;
  el.textContent = message;
  region.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function askConfirm(message) {
  const modal = document.getElementById("confirm-modal");
  const body = document.getElementById("confirm-body");
  const okBtn = document.getElementById("confirm-ok");
  const cancelBtn = document.getElementById("confirm-cancel");
  if (!modal || !body || !okBtn || !cancelBtn) {
    return Promise.resolve(window.confirm(message));
  }
  body.textContent = message;
  modal.classList.remove("hidden");
  return new Promise((resolve) => {
    const done = (value) => {
      modal.classList.add("hidden");
      okBtn.onclick = null;
      cancelBtn.onclick = null;
      resolve(value);
    };
    okBtn.onclick = () => done(true);
    cancelBtn.onclick = () => done(false);
  });
}

async function runAction(name, params = {}, { confirm = false } = {}) {
  const buttons = [...document.querySelectorAll(`[data-action="${name}"]`)];
  buttons.forEach((b) => (b.disabled = true));
  try {
    const body = { ...params };
    if (confirm || body.confirm) body.confirm = true;
    const res = await fetch(`/api/actions/${encodeURIComponent(name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const msg = data.hint ? `${data.error || "Failed"} — ${data.hint}` : (data.error || "Action failed");
      toast(msg, true);
      return data;
    }
    toast(data.message || `${name} ok`);
    if (name === "screenshot" && (data.filename || data.path || data.media)) {
      const filename = data.filename || (data.path || data.media || "").split("/").pop();
      const img = document.getElementById("shot-img");
      const empty = document.getElementById("shot-empty");
      if (img && filename) {
        img.src = `/media/${filename}?t=${Date.now()}`;
        img.classList.remove("hidden");
        empty?.classList.add("hidden");
      }
    }
    return data;
  } catch (err) {
    toast(err.message || String(err), true);
    return { ok: false, error: String(err) };
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}

document.addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-action]");
  if (!btn) return;
  const action = btn.getAttribute("data-action");
  let params = {};
  const raw = btn.getAttribute("data-params");
  if (raw) {
    try { params = JSON.parse(raw); } catch (_) { /* ignore */ }
  }
  const needsConfirm = btn.getAttribute("data-confirm") === "true";
  if (needsConfirm) {
    const ok = await askConfirm(`Run “${action}”?`);
    if (!ok) return;
    params.confirm = true;
  }
  await runAction(action, params, { confirm: needsConfirm });
});
