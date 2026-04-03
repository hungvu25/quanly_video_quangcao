async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {
    headers,
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
const browseDirEl = document.getElementById("browseDir");
const dirListEl = document.getElementById("dirList");
const uploadFileEl = document.getElementById("uploadFile");

let currentBrowsePath = "/videos";

async function renderVideos() {
  const data = await api("/api/videos");
  const videos = data.items || [];

  if (!videos.length) {
    videoListEl.innerHTML = '<div class="item">Chưa có video trong thư viện</div>';
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
            <button data-action="add" data-id="${video.id}">Thêm vào playlist</button>
            <button data-action="delete-video" data-id="${video.id}">Xóa</button>
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
    playlistListEl.innerHTML = '<div class="item">Playlist đang trống</div>';
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
            <button data-action="up" data-id="${item.id}">Lên</button>
            <button data-action="down" data-id="${item.id}">Xuống</button>
            <button data-action="remove-item" data-id="${item.id}">Bỏ</button>
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
    <div><strong>Trạng thái:</strong> ${status}</div>
    <div><strong>Đang phát mục:</strong> ${state.current_playlist_item_id || "không có"}</div>
    <div><strong>Lỗi:</strong> ${error || "không có"}</div>
  `;
}

async function renderDirectory(path = currentBrowsePath) {
  const data = await api(`/api/files/list?path=${encodeURIComponent(path)}`);
  currentBrowsePath = data.current_path;
  browseDirEl.value = currentBrowsePath;

  const entries = data.entries || [];
  const parentButton = data.parent_path
    ? `<button data-action="open-dir" data-path="${data.parent_path}">.. (thư mục cha)</button>`
    : "";

  if (!entries.length) {
    dirListEl.innerHTML = `${parentButton}<div class="item">Thư mục trống</div>`;
    return;
  }

  dirListEl.innerHTML = `
    ${parentButton}
    ${entries
      .map((entry) => {
        if (entry.type === "dir") {
          return `
            <div class="item">
              <div class="meta">
                <div class="name">[DIR] ${entry.name}</div>
                <div class="path">${entry.path}</div>
              </div>
              <div class="actions">
                <button data-action="open-dir" data-path="${entry.path}">Mở</button>
                <button data-action="set-scan-dir" data-path="${entry.path}">Đặt làm thư mục quét</button>
              </div>
            </div>
          `;
        }

        return `
          <div class="item">
            <div class="meta">
              <div class="name">${entry.name}</div>
              <div class="path">${entry.path}</div>
            </div>
          </div>
        `;
      })
      .join("")}
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
    alert("Nhập đường dẫn thư mục video");
    return;
  }

  try {
    const result = await api("/api/videos/scan", {
      method: "POST",
      body: JSON.stringify({ directory }),
    });
    await renderVideos();
    alert(`Đã quét ${result.imported} file`);
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("btnBrowse").addEventListener("click", async () => {
  const path = browseDirEl.value.trim() || "/videos";
  try {
    await renderDirectory(path);
  } catch (err) {
    alert(err.message);
  }
});

dirListEl.addEventListener("click", async (event) => {
  const btn = event.target.closest("button");
  if (!btn) {
    return;
  }

  const action = btn.dataset.action;
  const path = btn.dataset.path;
  if (!path) {
    return;
  }

  try {
    if (action === "open-dir") {
      await renderDirectory(path);
      return;
    }

    if (action === "set-scan-dir") {
      scanDirEl.value = path;
      browseDirEl.value = path;
      currentBrowsePath = path;
    }
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("btnUpload").addEventListener("click", async () => {
  const file = uploadFileEl.files && uploadFileEl.files[0];
  if (!file) {
    alert("Chọn file video để upload");
    return;
  }

  const form = new FormData();
  form.append("file", file);
  form.append("target_dir", currentBrowsePath || "/videos");

  try {
    await api("/api/videos/upload", {
      method: "POST",
      body: form,
    });
    uploadFileEl.value = "";
    await Promise.all([renderVideos(), renderDirectory(currentBrowsePath)]);
    alert("Upload thành công");
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
    await Promise.all([
      renderVideos(),
      renderPlaylist(),
      renderStatus(),
      renderDirectory(currentBrowsePath),
    ]);
  } catch (err) {
    statusBoxEl.classList.add("error");
    statusBoxEl.textContent = err.message;
  }
}

refreshAll();
setInterval(renderStatus, 2000);
