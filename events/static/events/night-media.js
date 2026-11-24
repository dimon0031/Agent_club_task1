const musicToggle = document.querySelector("#music-toggle");
const musicState = document.querySelector("#music-state");
const panel = document.querySelector("#playlist");
const playerLink = document.querySelector("#player-link");
const status = document.querySelector("#playlist-status");
const slot = document.querySelector("#player-slot");
const playButton = document.querySelector("#music-play");
const beat = document.querySelector("#local-beat");
const beatButton = document.querySelector("#beat-play");
beat.volume = 0.23;
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
  beat.pause();
  beatButton.hidden = false;
  savePreference(enabled);
  if (player) player.destroy();
  player = undefined;
  slot.replaceChildren();
  panel.hidden = playerLink.hidden = !enabled;
  playButton.hidden = true;
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
    let startWhenCued = true;
    player = new YT.Player(mount, {
      width: "100%", height: "220",
      videoId: tracks[index],
      playerVars: { playsinline: 1, origin: location.origin },
      events: {
        onReady({ target }) {
          if (generation !== request) return;
          clearTimeout(slowLoad);
          target.getIframe().title = "Нічний плейліст YouTube";
          musicState.textContent = "готова";
          status.textContent = "Для запуску зі звуком натисніть «Відтворити плейліст».";
          playButton.hidden = false;
          target.setVolume(23);
          target.cuePlaylist(tracks, index, seconds);
          target.setLoop(true);
        },
        onStateChange({ data, target }) {
          if (generation !== request) return;
          if (data === YT.PlayerState.CUED && startWhenCued) {
            startWhenCued = false;
            target.playVideo();
          } else if (data === YT.PlayerState.PLAYING) {
            playButton.hidden = true;
            status.textContent = "";
            musicState.textContent = "увімк.";
          } else if (data === YT.PlayerState.PAUSED) {
            playButton.hidden = false;
            musicState.textContent = "пауза";
          }
        },
        onAutoplayBlocked() {
          if (generation !== request) return;
          playButton.hidden = false;
          status.textContent = "Браузер очікує натискання «Відтворити плейліст».";
          musicState.textContent = "пауза";
        },
        onError({ data }) {
          if (generation !== request) return;
          clearTimeout(slowLoad);
          playButton.hidden = true;
          status.textContent = [101, 150].includes(data)
            ? "YouTube обмежив відтворення у вбудованому програвачі. Відкрийте плейліст на YouTube або ввімкніть локальний біт."
            : unavailable;
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
musicToggle.addEventListener("click", () => {
  const opening = panel.hidden;
  setMusic(opening);
  if (opening) panel.scrollIntoView({block: "center"});
});
playButton.addEventListener("click", () => {
  player.unMute();
  player.playVideo();
});
beatButton.addEventListener("click", async () => {
  ++generation;
  bookmark();
  if (player) player.destroy();
  player = undefined;
  slot.replaceChildren();
  playButton.hidden = true;
  try {
    await beat.play();
    if (beat.paused || panel.hidden) return;
    beatButton.hidden = true;
    status.textContent = "Грає локальний клубний біт.";
    musicState.textContent = "локальний біт";
  } catch {
    status.textContent = "Не вдалося відтворити локальний біт. Спробуйте ще раз.";
  }
});
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
