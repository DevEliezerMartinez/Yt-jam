// ── Config ────────────────────────────────────────────────────────────────
// Cambia esta URL por la que te dé Cloudflare Tunnel
const SERVER_URL = "https://jam.demail.store";

// Debe coincidir con SECRET_KEY en el .env del servidor
const SECRET_KEY = "oficina-2025-mktsecreto";
// ── Helpers ───────────────────────────────────────────────────────────────
function getVideoId(url) {
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtube.com")) {
      return u.searchParams.get("v");
    }
    if (u.hostname === "youtu.be") {
      return u.pathname.slice(1);
    }
  } catch (_) {}
  return null;
}

function setStatus(msg, type) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = `status ${type}`;
}

function clearStatus() {
  const el = document.getElementById("status");
  el.className = "status";
  el.textContent = "";
}

// ── Init: detectar tab activo ─────────────────────────────────────────────
let currentVideoId = null;
let currentVideoTitle = null;

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  if (!tab) return;

  const videoId = getVideoId(tab.url);
  const btn = document.getElementById("btn-add");

  if (videoId) {
    currentVideoId = videoId;
    currentVideoTitle =
      tab.title?.replace(" - YouTube", "").trim() || "Video sin título";

    document.getElementById("no-video").style.display = "none";
    document.getElementById("video-data").style.display = "block";
    document.getElementById("video-title").textContent = currentVideoTitle;
    document.getElementById("video-id").textContent = `ID: ${videoId}`;
    btn.disabled = false;
  }
});

// ── Botón agregar ─────────────────────────────────────────────────────────
document.getElementById("btn-add").addEventListener("click", async () => {
  if (!currentVideoId) return;

  const btn = document.getElementById("btn-add");
  btn.disabled = true;
  setStatus("Agregando…", "loading");

  try {
    const res = await fetch(`${SERVER_URL}/queue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        videoId: currentVideoId,
        title: currentVideoTitle,
        secret: SECRET_KEY,
      }),
    });

    if (res.ok) {
      setStatus("✓ Agregado a la cola", "success");
      // Cerrar popup automáticamente tras 1.5 s
      setTimeout(() => window.close(), 1500);
    } else {
      const data = await res.json().catch(() => ({}));
      setStatus(`Error: ${data.detail || res.status}`, "error");
      btn.disabled = false;
    }
  } catch (err) {
    setStatus("No se pudo conectar al servidor", "error");
    btn.disabled = false;
  }
});
