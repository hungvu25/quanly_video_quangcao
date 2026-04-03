async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      // Ignore JSON parse failures for non-JSON responses.
    }
    throw new Error(message);
  }

  return res.json();
}

const videoListEl = document.getElementById("videoList");
const playlistListEl = document.getElementById("playlistList");
const statusBoxEl = document.getElementById("statusBox");
const scanDirEl = document.getElementById("scanDir");

async function renderVideos() {
  const data = await api("/api/videos");
  const videos = data.items || [];

  if (!videos.length) {
    videoListEl.innerHTML = '<div class="item">Chua co video trong thu vien</div>';
    return;
  }

  videoListEl.innerHTML = videos
    .map(
      (video) => `
        <div class="item">
          <div class="meta">
            <div class="name">${video.name}</div>
            <div class="path">${video.path}</div>
          </div>
          <div class="actions">
            <button data-action="add" data-id="${video.id}">Them vao playlist</button>
            <button data-action="delete-video" data-id="${video.id}">Xoa</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function renderPlaylist() {
  const data = await api("/api/playlist");
  const items = data.items || [];

  if (!items.length) {
    playlistListEl.innerHTML = '<div class="item">Playlist dang trong</div>';
    return;
  }

  playlistListEl.innerHTML = items
    .map(
      (item, index) => `
        <div class="item">
          <div class="meta">
            <div class="name">#${index + 1} ${item.name}</div>
            <div class="path">${item.path}</div>
          </div>
          <div class="actions">
            <button data-action="up" data-id="${item.id}">Len</button>
            <button data-action="down" data-id="${item.id}">Xuong</button>
            <button data-action="remove-item" data-id="${item.id}">Bo</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function renderStatus() {
  const data = await api("/api/player/status");
  const state = data.state || {};
  const status = state.status || "idle";
  const error = state.error_message || "";

  statusBoxEl.classList.toggle("error", Boolean(error));
  statusBoxEl.innerHTML = `
    <div><strong>Trang thai:</strong> ${status}</div>
    <div><strong>Dang phat item:</strong> ${state.current_playlist_item_id || "none"}</div>
    <div><strong>Loi:</strong> ${error || "none"}</div>
  `;
}

async function reorderItem(targetItemId, direction) {
  const data = await api("/api/playlist");
  const ids = (data.items || []).map((x) => x.id);
  const index = ids.indexOf(targetItemId);

  if (index === -1) {
    return;
  }

  const swapWith = direction === "up" ? index - 1 : index + 1;
  if (swapWith < 0 || swapWith >= ids.length) {
    return;
  }

  const temp = ids[index];
  ids[index] = ids[swapWith];
  ids[swapWith] = temp;

  await api("/api/playlist/reorder", {
    method: "POST",
    body: JSON.stringify({ ordered_item_ids: ids }),
  });
}

videoListEl.addEventListener("click", async (event) => {
  const btn = event.target.closest("button");
  if (!btn) {
    return;
  }

  const action = btn.dataset.action;
  const id = Number(btn.dataset.id);

  try {
    if (action === "add") {
      await api("/api/playlist/add", {
        method: "POST",
        body: JSON.stringify({ video_id: id }),
      });
      await renderPlaylist();
      return;
    }

    if (action === "delete-video") {
      await api(`/api/videos/${id}`, { method: "DELETE" });
      await Promise.all([renderVideos(), renderPlaylist()]);
    }
  } catch (err) {
    alert(err.message);
  }
});

playlistListEl.addEventListener("click", async (event) => {
  const btn = event.target.closest("button");
  if (!btn) {
    return;
  }

  const action = btn.dataset.action;
  const id = Number(btn.dataset.id);

  try {
    if (action === "remove-item") {
      await api(`/api/playlist/${id}`, { method: "DELETE" });
    }

    if (action === "up" || action === "down") {
      await reorderItem(id, action);
    }

    await renderPlaylist();
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("btnScan").addEventListener("click", async () => {
  const directory = scanDirEl.value.trim();
  if (!directory) {
    alert("Nhap duong dan thu muc video");
    return;
  }

  try {
    const result = await api("/api/videos/scan", {
      method: "POST",
      body: JSON.stringify({ directory }),
    });
    await renderVideos();
    alert(`Da quet ${result.imported} file`);
  } catch (err) {
    alert(err.message);
  }
});

async function control(path) {
  try {
    await api(path, { method: "POST" });
    await renderStatus();
  } catch (err) {
    alert(err.message);
  }
}

document.getElementById("btnStart").addEventListener("click", () => control("/api/player/start"));
document.getElementById("btnPause").addEventListener("click", () => control("/api/player/pause"));
document.getElementById("btnNext").addEventListener("click", () => control("/api/player/next"));
document.getElementById("btnStop").addEventListener("click", () => control("/api/player/stop"));

async function refreshAll() {
  try {
    await Promise.all([renderVideos(), renderPlaylist(), renderStatus()]);
  } catch (err) {
    statusBoxEl.classList.add("error");
    statusBoxEl.textContent = err.message;
  }
}

refreshAll();
setInterval(renderStatus, 2000);
