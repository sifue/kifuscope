const panel = document.querySelector(".panel");
const score = document.querySelector("#score");
const bestmove = document.querySelector("#bestmove");
const depth = document.querySelector("#depth");
const status = document.querySelector("#status");
const senteBar = document.querySelector("#sente-bar");
const barLabel = document.querySelector("#bar-label");
const controls = document.querySelector("#controls");
const resetTracker = document.querySelector("#reset-tracker");

if (new URLSearchParams(location.search).get("controls") === "1") {
  controls.classList.remove("hidden");
}

resetTracker.addEventListener("click", async () => {
  status.textContent = "追跡状態をリセット中";
  try {
    const response = await fetch("/api/realtime/reset", { method: "POST" });
    update(await response.json());
  } catch {
    status.textContent = "追跡リセットに失敗しました";
  }
});

function formatScore(data) {
  if (data.score_type === "mate" && data.mate_sente !== null) {
    const side = data.mate_sente > 0 ? "先手" : "後手";
    return `${side} 詰みまで ${Math.abs(data.mate_sente)}手`;
  }
  if (data.eval_cp_sente !== null && data.eval_cp_sente !== undefined) {
    const side = data.eval_cp_sente >= 0 ? "先手" : "後手";
    return `${side} ${data.eval_cp_sente >= 0 ? "+" : ""}${data.eval_cp_sente}`;
  }
  return "評価待ち";
}

function update(data) {
  const ok = data.status === "ok";
  panel.classList.toggle("error", !ok && !["waiting", "evaluating"].includes(data.status));
  score.textContent = formatScore(data);
  bestmove.textContent = data.bestmove_japanese || data.bestmove || "—";
  depth.textContent = `深さ ${data.depth ?? "—"}`;
  status.textContent = data.message || data.status;
  const cp = data.eval_cp_sente ?? 0;
  const percentage = 50 + 45 * Math.tanh(cp / 600);
  senteBar.style.width = `${Math.max(5, Math.min(95, percentage))}%`;
  barLabel.textContent = Math.abs(cp) < 100 ? "互角" : cp > 0 ? "先手優勢" : "後手優勢";
}

function connect() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${location.host}/ws/eval`);
  socket.onmessage = (event) => update(JSON.parse(event.data));
  socket.onopen = () => socket.send("subscribe");
  socket.onclose = () => {
    status.textContent = "サーバーへ再接続中";
    setTimeout(connect, 1500);
  };
}

fetch("/api/eval").then((response) => response.json()).then(update).catch(() => {});
connect();
