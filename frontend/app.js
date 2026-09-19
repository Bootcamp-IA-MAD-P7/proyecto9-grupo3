"use strict";

let token = null;
let user = null;
let selected = null;
let page = 1;
let hasNext = false;
const $ = (id) => document.getElementById(id);

function notice(message) { $("notice").textContent = message; }

async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}),
                    ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  let response;
  try { response = await fetch(path, { ...options, headers, cache: "no-store" }); }
  catch { throw new Error("No se pudo conectar con el servidor."); }
  if (response.status === 401 && token) clearSession();
  if (!response.ok) {
    const details = await response.json().catch(() => ({}));
    const messages = { 401: "Sesión no válida. Vuelve a entrar.", 403: "No tienes permiso para esta acción.",
                       409: "El estado cambió. Actualiza la lista e inténtalo de nuevo.",
                       422: "Comprueba los datos del formulario.", 503: "La puntuación no está disponible." };
    const error = new Error(messages[response.status] || details.detail || `Error ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

async function run(task) {
  notice("Cargando…");
  try { await task(); }
  catch (error) {
    if (error.status === 409 && token) {
      clearSelection();
      try { await loadQueue(); await loadAssigned(); } catch { /* Show original conflict. */ }
    }
    notice(error.message);
  }
}

function clearSelection() {
  selected = null;
  $("selection").textContent = "Selecciona un elemento de la cola.";
  $("comment-text").textContent = "";
  $("comment-text").hidden = true;
  $("review-form").hidden = true;
  $("history-list").replaceChildren();
  for (const id of ["claim", "reveal", "history"]) $(id).disabled = true;
}

function clearSession() {
  token = null; user = null; clearSelection();
  $("workspace").hidden = true; $("login-panel").hidden = false;
  $("queue").replaceChildren(); $("assigned").replaceChildren(); $("escalations").replaceChildren();
  $("reopen-requests").replaceChildren();
}

function selectComment(item) {
  clearSelection(); selected = item.comment_id;
  $("selection").textContent = `${item.comment_id} · vídeo ${item.video_id} · puntuación ${item.risk_score.toFixed(3)} · ${item.model_version}`;
  $("claim").disabled = item.status !== "PENDING";
  $("reveal").disabled = item.status !== "IN_REVIEW";
  $("history").disabled = false;
}

async function loadAssigned() {
  const data = await api("/comments/assigned");
  $("assigned").replaceChildren();
  if (!data.length) $("assigned").textContent = "No tienes comentarios asignados.";
  for (const item of data) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${item.comment_id} · ${item.video_id} · asignado a ti`;
    button.addEventListener("click", () => selectComment(item));
    $("assigned").append(button);
  }
}

async function loadQueue() {
  const data = await api(`/comments/queue?page=${page}&page_size=20`);
  hasNext = data.has_next;
  $("page-label").textContent = `Página ${page} · ${data.total} pendientes`;
  $("previous-page").disabled = page === 1;
  $("next-page").disabled = !hasNext;
  $("queue").replaceChildren();
  if (!data.items.length) $("queue").textContent = "No hay comentarios pendientes.";
  for (const item of data.items) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${item.comment_id} · ${item.video_id} · ${item.risk_score.toFixed(3)} · ${item.score_source}`;
    button.addEventListener("click", () => selectComment(item));
    $("queue").append(button);
  }
  notice("Cola actualizada.");
}

function formData(id) { return Object.fromEntries(new FormData($(id))); }

$("login-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const data = await api("/auth/login", { method: "POST", body: JSON.stringify(formData("login-form")) });
    token = data.access_token; user = data.user;
    $("login-form").reset();
    $("identity").textContent = `${user.display_name} · ${user.role}`;
    $("login-panel").hidden = true; $("workspace").hidden = false;
    $("supervisor-panel").hidden = user.role !== "SUPERVISOR";
    await loadQueue(); await loadAssigned();
  });
});
$("logout").addEventListener("click", () => run(async () => {
  try { await api("/auth/logout", { method: "POST" }); } finally { clearSession(); notice("Sesión cerrada."); }
}));
$("refresh-queue").addEventListener("click", () => run(loadQueue));
$("refresh-assigned").addEventListener("click", () => run(async () => {
  await loadAssigned(); notice("Asignaciones actualizadas.");
}));
$("previous-page").addEventListener("click", () => run(async () => { page--; clearSelection(); await loadQueue(); }));
$("next-page").addEventListener("click", () => run(async () => { page++; clearSelection(); await loadQueue(); }));
$("claim").addEventListener("click", () => run(async () => {
  await api(`/comments/${encodeURIComponent(selected)}/claim`, { method: "POST" });
  $("claim").disabled = true; $("reveal").disabled = false;
  await loadQueue(); await loadAssigned();
  notice("Comentario asignado. Ahora puedes mostrar el texto.");
}));
$("reveal").addEventListener("click", () => run(async () => {
  const data = await api(`/comments/${encodeURIComponent(selected)}/content`);
  $("comment-text").textContent = data.text; $("comment-text").hidden = false;
  $("review-form").hidden = false; notice("Texto mostrado solo para tu asignación.");
}));
$("review-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(async () => {
    await api(`/comments/${encodeURIComponent(selected)}/reviews`, {
      method: "POST", body: JSON.stringify(formData("review-form")),
    });
    const reviewedId = selected;
    clearSelection(); $("review-form").reset(); await loadQueue(); await loadAssigned();
    $("history-form").querySelector('[name="comment_id"]').value = reviewedId;
    await showHistory(reviewedId); notice("Revisión guardada. Historial disponible abajo.");
  });
});
async function showHistory(commentId) {
  const data = await api(`/comments/${encodeURIComponent(commentId)}/history`);
  $("history-list").replaceChildren();
  for (const event of data.events) {
    const row = document.createElement("p");
    row.textContent = `${event.event_type} · ${event.actor_display_name || "sistema"} · ${event.reason || ""}`;
    $("history-list").append(row);
  }
  notice(`Historial de ${commentId} actualizado.`);
}
$("history").addEventListener("click", () => run(() => showHistory(selected)));
$("history-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(() => showHistory(formData("history-form").comment_id));
});
$("import-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(async () => {
    const lines = formData("import-form").items.split(/\r?\n/).filter(Boolean);
    const items = lines.map((line) => {
      const [comment_id, video_id, ...text] = line.split("|").map((value) => value.trim());
      return { comment_id, video_id, text: text.join("|") };
    });
    const data = await api("/comments/import", { method: "POST", body: JSON.stringify({ items }) });
    $("import-form").reset(); await loadQueue(); notice(`${data.imported} comentarios importados.`);
  });
});
async function listInto(path, target, render) {
  const data = await api(path); $(target).replaceChildren();
  if (!data.length) $(target).textContent = "Sin elementos.";
  for (const item of data) {
    const row = document.createElement("p"); row.textContent = render(item); $(target).append(row);
  }
  notice("Lista actualizada.");
}
$("refresh-escalations").addEventListener("click", () => run(() => listInto(
  "/supervisor/escalations", "escalations", (item) => `${item.comment_id} · ${item.video_id} · ${item.status}`)));
$("refresh-reopen").addEventListener("click", () => run(() => listInto(
  "/supervisor/reopen-requests", "reopen-requests", (item) => `${item.request_id} · ${item.comment_id} · ${item.status}`)));
for (const [form, action] of [["resolve-form", "resolve"], ["reassign-form", "reassign"]]) {
  $(form).addEventListener("submit", (event) => {
    event.preventDefault(); run(async () => {
      const { comment_id, ...body } = formData(form);
      if (action === "resolve") body.recommend_removal = body.recommend_removal === "on";
      await api(`/supervisor/comments/${encodeURIComponent(comment_id)}/${action}`, {
        method: "POST", body: JSON.stringify(body),
      });
      $(form).reset(); notice("Acción de supervisión guardada.");
    });
  });
}
$("reopen-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(async () => {
    const { comment_id, ...body } = formData("reopen-form");
    await api(`/comments/${encodeURIComponent(comment_id)}/reopen-requests`, {
      method: "POST", body: JSON.stringify(body),
    });
    $("reopen-form").reset(); notice("Solicitud de reapertura registrada.");
  });
});
$("reopen-info-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(async () => {
    const { comment_id, request_id, note } = formData("reopen-info-form");
    await api(`/comments/${encodeURIComponent(comment_id)}/reopen-requests/${encodeURIComponent(request_id)}/information`, {
      method: "POST", body: JSON.stringify({ note }),
    });
    $("reopen-info-form").reset(); notice("Información enviada.");
  });
});
$("reopen-decision-form").addEventListener("submit", (event) => {
  event.preventDefault(); run(async () => {
    const { request_id, action, reason } = formData("reopen-decision-form");
    await api(`/supervisor/reopen-requests/${encodeURIComponent(request_id)}/${action}`, {
      method: "POST", body: JSON.stringify({ reason }),
    });
    $("reopen-decision-form").reset(); notice("Decisión de reapertura guardada.");
  });
});
