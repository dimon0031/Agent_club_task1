const audio = document.querySelector("#music");
const musicToggle = document.querySelector("#music-toggle");
const musicState = document.querySelector("#music-state");

function remember(enabled) {
  try {
    localStorage.setItem("night.music", enabled ? "on" : "off");
  } catch { /* Playback also works without browser storage. */ }
}

function showMusicState() {
  const playing = !audio.paused && !audio.error;
  musicToggle.setAttribute("aria-pressed", String(playing));
  musicState.textContent = playing ? "увімк." : "вимк.";
}

async function startMusic() {
  try {
    await audio.play();
    remember(true);
  } catch {
    // A browser can require a new gesture after navigation.
    showMusicState();
  }
}

audio.volume = 0.23;
musicToggle.hidden = false;
audio.addEventListener("playing", showMusicState);
audio.addEventListener("pause", showMusicState);
audio.addEventListener("error", () => {
  musicToggle.disabled = true;
  musicState.textContent = "недоступна";
  musicToggle.setAttribute("aria-pressed", "false");
});
musicToggle.addEventListener("click", () => {
  if (audio.paused) {
    startMusic();
  } else {
    remember(false);
    audio.pause();
  }
});
try {
  if (localStorage.getItem("night.music") === "on") {
    audio.currentTime = Number(sessionStorage.getItem("night.position")) || 0;
    startMusic();
  }
} catch { /* A first visit starts silent. */ }
window.addEventListener("pagehide", () => {
  try { sessionStorage.setItem("night.position", String(audio.currentTime)); } catch {}
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
