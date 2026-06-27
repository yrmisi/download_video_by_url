let currentTaskId = null;

// Инициализация или получение User ID
let userId = localStorage.getItem("media_grab_user_id");
if (!userId) {
  userId = crypto.randomUUID();
  localStorage.setItem("media_grab_user_id", userId);
}

// Форматирование размера файлов
function formatSize(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Форматирование длительности видео
function formatDuration(seconds) {
  if (!seconds) return "";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  let ret = "";
  if (hrs > 0) {
    ret += "" + hrs + ":" + (mins < 10 ? "0" : "");
  }
  ret += "" + mins + ":" + (secs < 10 ? "0" : "");
  ret += "" + secs;
  return ret;
}

// Безопасное экранирование HTML строк
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Повторный запуск из блока истории
async function reDownload(url) {
  if (!url) return;

  const urlInput = document.getElementById("video-url");
  urlInput.value = url;
  urlInput.classList.add("border-blue-500");

  await fetchInfo();

  urlInput.classList.remove("border-blue-500");
}

// Загрузка истории с сервера
async function fetchHistory() {
  const historyList = document.getElementById("history-list");
  const historySection = document.getElementById("history-section");

  try {
    const response = await fetch("/api/recent-history/" + userId);
    const history = await response.json();

    if (!history || history.length === 0) {
      historySection.classList.add("hidden");
      return;
    }

    historySection.classList.remove("hidden");

    historyList.innerHTML = history
      .map((item) => {
        const id = item.id;
        const downloadUrl = "/api/files/" + id;

        // Экранируем URL для data-атрибута
        const safeUrl = escapeHtml(item.url);
        const safeTitle = escapeHtml(item.title || "Untitled");
        const safeResolution = escapeHtml(item.resolution || "N/A");
        const safeStatus = escapeHtml(item.status);

        let html = `<div data-url="${safeUrl}" onclick="reDownload(this.dataset.url)" class="flex items-center space-x-4 bg-[#333] p-3 rounded-lg hover:bg-[#383838] transition border border-transparent hover:border-gray-600 cursor-pointer group">`;

        html += '<div class="relative w-16 h-10 flex-shrink-0">';
        html += `<img src="${escapeHtml(item.thumbnail)}" class="w-full h-full object-cover rounded shadow-md" onerror="this.src='https://via.placeholder.com/64x40?text=Video'">`;

        if (item.duration) {
          html +=
            '<span class="absolute bottom-1 right-1 bg-black/80 text-white text-[9px] px-1 rounded">' +
            formatDuration(item.duration) +
            "</span>";
        }
        html += "</div>";

        html += '<div class="flex-1 min-w-0">';
        html += `<p class="text-sm font-medium truncate text-gray-200">${safeTitle}</p>`;

        html +=
          '<div class="flex items-center text-xs text-gray-400 space-x-2">';
        html += `<span class="bg-gray-700 px-1 rounded">${safeResolution}</span>`;
        html += "<span>•</span>";
        html +=
          "<span>" +
          (item.filesize ? formatSize(item.filesize) : "Unknown size") +
          "</span>";
        html += "<span>•</span>";

        let statusColor = "text-blue-400";
        if (item.status === "deleted") statusColor = "text-red-400";

        html += `<span class="${statusColor}">${safeStatus}</span>`;
        html += "</div></div>";

        if (item.status === "finished") {
          html += `<a href="${downloadUrl}" class="text-gray-400 hover:text-blue-500 p-2 z-10" download onclick="event.stopPropagation()">`;
          html +=
            '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">';
          html +=
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />';
          html += "</svg></a>";
        } else if (item.status === "deleted") {
          html +=
            '<span class="text-gray-600 p-2" title="File deleted due to timeout">🗑️</span>';
        }

        html += "</div>";
        return html;
      })
      .join("");
  } catch (e) {
    console.error("Failed to fetch history", e);
  }
}

// Навигация по шагам интерфейса с управлением фокусом
function showStep(step) {
  const stepInput = document.getElementById("step-input");
  const stepPreview = document.getElementById("step-preview");
  const stepProgress = document.getElementById("step-progress");

  stepInput.classList.add("hidden");
  stepPreview.classList.add("hidden");
  stepProgress.classList.add("hidden");

  const activeStepContainer = document.getElementById("step-" + step);
  if (activeStepContainer) {
    activeStepContainer.classList.remove("hidden");
    // Переносим фокус на новый контейнер для экранных дикторов
    activeStepContainer.focus();
  }

  const historySection = document.getElementById("history-section");
  if (step === "input") {
    fetchHistory();
  } else {
    historySection.classList.add("hidden");
  }
}

// Получение информации о медиафайле с профессиональной индикацией загрузки и a11y
async function fetchInfo() {
  const urlInput = document.getElementById("video-url");
  const url = urlInput.value.trim(); // Защита от случайных пробелов
  if (!url) return alert("Enter URL");

  const btn = document.getElementById("btn-continue");

  // 1. Входим в состояние загрузки: блокируем элементы управления
  btn.disabled = true;
  urlInput.disabled = true;
  btn.setAttribute("aria-disabled", "true"); // Сигнал диктору

  // Добавляем понятный UX: меняем курсор и делаем элементы визуально "занятыми"
  btn.classList.add("opacity-70", "cursor-not-allowed");
  urlInput.classList.add("opacity-50", "cursor-not-allowed");

  // Сохраняем исходный контент кнопки и вставляем красивый SVG-спиннер
  const originalBtnText = btn.innerHTML;
  btn.innerHTML = `
    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    Extracting info...
  `;

  try {
    const response = await fetch("/api/extract-info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url }),
    });

    const data = await response.json();

    // Проверяем статус ответа бэкенда
    if (!response.ok) {
      alert(data.detail || "Error fetching video info from server");
      return;
    }

    if (!data || !data.thumbnail) {
      alert("Сервер вернул пустые данные или отсутствует превью.");
      return;
    }

    // Обновляем DOM данными из ответа
    document.getElementById("video-title").innerText = data.title || "Untitled";
    document.getElementById("video-thumb").src = data.thumbnail;

    // Логика фильтрации качества
    const qualitySelect = document.getElementById("quality");
    const allQualities = [
      { v: "bestaudio", t: "Best Audio" },
      { v: "2160", t: "2160p (4K)" },
      { v: "1440", t: "1440p (2K)" },
      { v: "1080", t: "1080p (Full HD)" },
      { v: "720", t: "720p (HD)" },
      { v: "480", t: "480p" },
      { v: "360", t: "360p" },
      { v: "240", t: "240p" },
      { v: "144", t: "144p" },
    ];

    const available = allQualities.filter(
      (q) => q.v === "bestaudio" || parseInt(q.v) <= (data.max_quality || 1080),
    );

    qualitySelect.innerHTML = available
      .map((q) => {
        const isAudio = q.v === "bestaudio";
        return `<option value="${q.v}" ${isAudio ? 'class="hidden"' : ""}>${q.t}</option>`;
      })
      .join("");

    const defaultVideoQuality = available.find((q) => q.v !== "bestaudio");
    if (defaultVideoQuality) {
      qualitySelect.value = defaultVideoQuality.v;
    }

    showStep("preview");
    updateQualityVisibility();
  } catch (e) {
    console.error("Fetch error:", e);
    alert("Network error or server is down");
  } finally {
    // 2. Гарантированно возвращаем интерфейс в рабочее состояние
    btn.disabled = false;
    urlInput.disabled = false;
    btn.removeAttribute("aria-disabled");

    btn.classList.remove("opacity-70", "cursor-not-allowed");
    urlInput.classList.remove("opacity-50", "cursor-not-allowed");

    btn.innerHTML = originalBtnText;
  }
}

// Управление видимостью селекта качества в зависимости от профиля
function updateQualityVisibility() {
  const profile = document.getElementById("profile").value;
  const qualityContainer = document.getElementById("quality-container");
  const qualitySelect = document.getElementById("quality");

  const shouldHide = ["audio_only", "mobile", "mp4"].includes(profile);

  if (shouldHide) {
    qualityContainer.classList.add("hidden");

    const setSafeQuality = (target) => {
      const exists = Array.from(qualitySelect.options).some(
        (opt) => opt.value === target,
      );
      if (exists) {
        qualitySelect.value = target;
      } else {
        const firstVideo = Array.from(qualitySelect.options).find(
          (opt) => opt.value !== "bestaudio",
        );
        if (firstVideo) qualitySelect.value = firstVideo.value;
      }
    };

    if (profile === "mobile") {
      setSafeQuality("720");
    } else if (profile === "mp4") {
      setSafeQuality("1080");
    } else if (profile === "audio_only") {
      qualitySelect.value = "bestaudio";
    }
  } else {
    qualityContainer.classList.remove("hidden");
  }
}

// Слушатели событий
document
  .getElementById("profile")
  .addEventListener("change", updateQualityVisibility);
document.addEventListener("DOMContentLoaded", fetchHistory);

// Запуск процесса скачивания задачи
async function startDownload() {
  const payload = {
    url: document.getElementById("video-url").value,
    user_id: userId,
    profile: document.getElementById("profile").value,
    quality: document.getElementById("quality").value,
  };

  const response = await fetch("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  currentTaskId = data.task_id;

  showStep("progress");
  pollStatus();
}

// Отмена скачивания
async function cancelDownload() {
  if (!currentTaskId) return;

  try {
    await fetch(`/api/cancel/${currentTaskId}`, { method: "POST" });
    location.reload();
  } catch (e) {
    console.error("Cancel failed", e);
    location.reload();
  }
}

// Лонг-пуллинг статуса задачи из бэкенда/Redis с защитой от зависаний
function pollStatus() {
  const progressBar = document.getElementById("progress-bar");
  const statusText = document.getElementById("status-text");
  const speedText = document.getElementById("speed-text");
  const downloadContainer = document.getElementById("download-ready-container");
  const downloadLink = document.getElementById("download-link");
  const progressContainer = document.getElementById("progress-container");

  let retries = 0;
  const MAX_RETRIES = 30;

  const interval = setInterval(async () => {
    if (!currentTaskId) {
      clearInterval(interval);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(`/api/status/${currentTaskId}`, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      retries = 0;

      if (data.status === "downloading") {
        progressBar.classList.remove("animate-pulse");
        const percent = data.percent || "0%";
        progressBar.style.width = percent;

        // Синхронизируем значение для скринридеров
        progressBar.setAttribute("aria-valuenow", parseInt(percent) || 0);

        statusText.innerText = `Downloading: ${percent}`;
        speedText.innerText = data.speed || "0 MB/s";
      } else if (data.status === "processing") {
        progressBar.style.width = "100%";
        progressBar.setAttribute("aria-valuenow", 100);
        progressBar.classList.add("animate-pulse");

        statusText.innerText = data.msg || "Processing video via FFmpeg...";
        speedText.innerText = "FFmpeg";
      } else if (data.status === "finished") {
        clearInterval(interval); // Чистим интервал строго один раз

        progressBar.style.width = "100%";
        progressBar.setAttribute("aria-valuenow", 100);
        progressBar.classList.remove("animate-pulse");
        statusText.innerText = "All set! Your download is ready.";
        speedText.innerText = "Done";

        const actionBtn = document.getElementById("action-button");
        actionBtn.innerText = "Home";
        actionBtn.onclick = () => location.reload();

        if (data.file_url) {
          progressContainer.classList.add("hidden");
          downloadLink.href = data.file_url;
          downloadLink.download = data.file_url.split("/").pop();
          downloadContainer.classList.remove("hidden");

          downloadLink.onclick = () => {
            setTimeout(() => {
              downloadContainer.classList.add("hidden");
              statusText.innerText = "File sent to browser";
            }, 500);
          };
        }
      }
    } catch (e) {
      clearTimeout(timeoutId);
      retries++;

      if (e.name === "AbortError") {
        console.warn(
          `Polling request timed out. Retry ${retries}/${MAX_RETRIES}`,
        );
        statusText.innerText = "Responding slowly...";
      } else {
        console.error("Polling network error:", e);
        statusText.innerText = `Connection lost... (${MAX_RETRIES - retries}s)`;
      }

      if (retries >= MAX_RETRIES) {
        clearInterval(interval);
        statusText.innerText = "Connection timeout. Please refresh page.";
        speedText.innerText = "Error";
        progressBar.classList.add("bg-red-500");
      }
    }
  }, 1000);
}
