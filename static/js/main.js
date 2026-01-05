// static/js/main.js
window.__MAIN_JS_LOADED__ = true;

let currentAudio = null;
let sleepMode = false;

window.stopAIvoice = function () {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
};

window.playAIvoice = async function (text) {
  if (!text) return;

  window.stopAIvoice();

  const instructions = sleepMode
    ? "幼児向けに、やさしく、ゆっくり読み聞かせしてください。文の間は少し間をあけてください。"
    : "子ども向けに、明るく、聞き取りやすく読み聞かせしてください。";

  const res = await fetch("/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      voice: "coral",
      instructions
    })
  });

  if (!res.ok) {
    const err = await res.text();
    alert("TTSエラー:\n" + err);
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);

  const audio = new Audio(url);
  currentAudio = audio;

  audio.onended = () => {
    URL.revokeObjectURL(url);
    if (currentAudio === audio) currentAudio = null;
  };

  // ※ クリックで呼べば autoplay ブロックを回避できる
  await audio.play();
};

// おやすみモード（見た目用）
window.addEventListener("DOMContentLoaded", () => {
  const sleepBtn = document.getElementById("sleepBtn");
  if (sleepBtn) {
    sleepBtn.addEventListener("click", () => {
      sleepMode = !sleepMode;
      document.body.classList.toggle("sleep", sleepMode);
      sleepBtn.textContent = sleepMode ? "🌙 おやすみモード：ON" : "🌙 おやすみモード：OFF";
    });
  }
});
