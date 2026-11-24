const musicToggle = document.querySelector("#music-toggle");
const musicState = document.querySelector("#music-state");
const panel = document.querySelector("#playlist");
const playerLink = document.querySelector("#player-link");
const status = document.querySelector("#playlist-status");
const slot = document.querySelector("#player-slot");
const tracks = Array.from(panel.querySelectorAll("ol a"), link =>
  new URL(link.href).searchParams.get("v")
);
let player;
let apiPromise;
let generation = 0;
let index = 0;
let seconds = 0;

function savePreference(enabled) {
  try {
    localStorage.setItem("night.playlist.enabled", String(enabled));
    sessionStorage.setItem("night.playlist.position", JSON.stringify([index, seconds]));
  } catch { /* Private browsing can disable storage. */ }
}

function bookmark() {
  if (!player?.getPlaylistIndex) return;
  const current = player.getPlaylistIndex();
  if (current >= 0) {
    index = current;
    seconds = player.getCurrentTime() || 0;
  }
}

function loadAPI() {
  if (window.YT?.Player) return Promise.resolve();
  if (!apiPromise) {
    apiPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      window.onYouTubeIframeAPIReady = resolve;
      script.onerror = () => {
        apiPromise = undefined;
        script.remove();
        reject(new Error("YouTube unavailable"));
      };
      script.src = "https://www.youtube.com/iframe_api";
      document.head.append(script);
    });
  }
  return apiPromise;
}

const unavailable = "YouTube недоступний. Можна відкрити трек за посиланням у списку.";
async function setMusic(enabled) {
  const request = ++generation;
  bookmark();
  savePreference(enabled);
  if (player) player.destroy();
  player = undefined;
  slot.replaceChildren();
  panel.hidden = playerLink.hidden = !enabled;
  musicToggle.setAttribute("aria-expanded", String(enabled));
  musicState.textContent = enabled ? "…" : "вимк.";
  if (!enabled) return;
  status.textContent = "Завантаження програвача…";
  const slowLoad = setTimeout(() => {
    if (generation === request && musicState.textContent === "…") {
      status.textContent = "Якщо програвач не завантажився, відкрийте трек за посиланням у списку.";
      musicState.textContent = "плейліст";
    }
  }, 9000);
  try {
    await loadAPI();
    if (generation !== request) return;
    const mount = document.createElement("div");
    slot.append(mount);
    player = new YT.Player(mount, {
      width: "100%", height: "220",
      playerVars: { playsinline: 1, origin: location.origin },
      events: {
        onReady({ target }) {
          if (generation !== request) return;
          clearTimeout(slowLoad);
          target.getIframe().title = "Нічний плейліст YouTube";
          musicState.textContent = "готова";
          status.textContent = "Якщо музика не почалася, натисніть ▶ у програвачі.";
          target.setVolume(23);
          target.loadPlaylist(tracks, index, seconds);
          target.setLoop(true);
        },
        onStateChange({ data }) {
          if (generation !== request) return;
          if (data === YT.PlayerState.PLAYING) {
            status.textContent = "";
            musicState.textContent = "увімк.";
          } else if (data === YT.PlayerState.PAUSED) {
            musicState.textContent = "пауза";
          }
        },
        onAutoplayBlocked() {
          if (generation !== request) return;
          status.textContent = "Натисніть ▶ у програвачі, щоб почати.";
          musicState.textContent = "пауза";
        },
        onError() {
          if (generation !== request) return;
          clearTimeout(slowLoad);
          status.textContent = unavailable;
          musicState.textContent = "недоступна";
        }
      }
    });
  } catch {
    clearTimeout(slowLoad);
    if (generation === request) {
      status.textContent = unavailable;
      musicState.textContent = "недоступна";
    }
  }
}

musicToggle.hidden = false;
musicToggle.addEventListener("click", () => setMusic(panel.hidden));
document.querySelector("#music-stop").addEventListener("click", () => {
  setMusic(false);
  musicToggle.focus();
});
try {
  const saved = JSON.parse(sessionStorage.getItem("night.playlist.position"));
  if (Array.isArray(saved) && Number.isInteger(saved[0]) && tracks[saved[0]]) {
    index = saved[0];
    seconds = Math.max(0, Number(saved[1]) || 0);
  }
  if (localStorage.getItem("night.playlist.enabled") === "true") setMusic(true);
} catch { /* A first visit starts silent. */ }
window.addEventListener("pagehide", () => {
  if (!panel.hidden) {
    bookmark();
    savePreference(true);
  }
});

const video = document.querySelector("#poster-video");
if (video) {
  const motionToggle = document.querySelector("#motion-toggle");
  const preference = matchMedia("(prefers-reduced-motion: reduce)");
  function syncMotion() {
    if (preference.matches) {
      video.pause();
      video.classList.remove("ready");
      motionToggle.hidden = true;
    } else {
      if (!video.hasAttribute("src")) video.src = video.dataset.src;
      motionToggle.hidden = false;
      video.play().catch(() => { motionToggle.textContent = "Увімкнути відео"; });
    }
  }
  video.addEventListener("playing", () => {
    video.classList.add("ready");
    motionToggle.textContent = "Пауза відео";
  });
  video.addEventListener("pause", () => { motionToggle.textContent = "Увімкнути відео"; });
  video.addEventListener("error", () => {
    video.classList.remove("ready");
    motionToggle.hidden = true;
  });
  motionToggle.addEventListener("click", () => {
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  });
  preference.addEventListener("change", syncMotion);
  syncMotion();
}
