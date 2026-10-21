/* The parallax.observer interface.
 *
 * A websocket chat, a monitoring bar, and the facts the agent used.
 */

const state = {
  socket: null,
  session: null,
  lastTurn: null,
};

const $ = (id) => document.getElementById(id);

/* ------------------------------------------------------------------ bar */

async function refreshStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();

    const llm = data.llm || {};
    $("m-llm").textContent =
      `${llm.model || "?"} | ${llm.requests || 0} req | ` +
      `${llm.avg_latency ? (llm.avg_latency * 1000).toFixed(0) : 0}ms | ` +
      `${llm.tokens_per_second || 0} tok/s`;

    const viking = data.viking || {};
    const corpus = viking.corpus || {};
    $("m-mem").textContent = viking.up
      ? `up | ${corpus.total_wisdoms || 0} wisdoms`
      : "not reachable";

    try {
      const gpu = await fetch("/api/gpu");
      const g = await gpu.json();
      if (g.error) {
        $("m-gpu").textContent = "no gpu";
      } else {
        $("m-gpu").textContent =
          `${g.name} | ${g.util}% | ` +
          `${(g.memory_used_mb / 1024).toFixed(1)}/${(g.memory_total_mb / 1024).toFixed(1)}GB`;
      }
    } catch {
      $("m-gpu").textContent = "no gpu";
    }
  } catch {
    $("m-llm").textContent = "app not reachable";
  }
}

setInterval(refreshStatus, 3000);
refreshStatus();

/* ---------------------------------------------------------------- setup */

$("setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    alterego: $("alterego").value.trim() || "Visitor",
    belief: $("belief").value,
    worldview: $("worldview").value,
  };

  const response = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    $("status").textContent = "could not start the session";
    return;
  }

  state.session = await response.json();
  $("setup").classList.add("hidden");
  $("chat").classList.remove("hidden");
  $("message").disabled = false;
  $("message").focus();
  connect();
});

/* ----------------------------------------------------------------- chat */

function connect() {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(
    `${scheme}://${location.host}/ws/${state.session.id}`
  );

  state.socket.onopen = () => {
    setStatus("up", `connected | ${state.session.worldview} | ` +
      `believing ${state.session.belief}`);
  };

  state.socket.onclose = () => {
    setStatus("down", "disconnected");
    $("message").disabled = true;
  };

  state.socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "ready") {
      state.session = data.session;
    } else if (data.type === "thinking") {
      showThinking(data.text);
    } else if (data.type === "reply") {
      clearThinking();
      showTurn(data.turn);
    } else if (data.type === "error") {
      clearThinking();
      setStatus("down", data.message);
    }
  };
}

function setStatus(cls, text) {
  const element = $("status");
  element.className = cls;
  element.textContent = text;
}

function showThinking(text) {
  clearThinking();
  const node = document.createElement("div");
  node.className = "turn thinking";
  node.id = "thinking";
  node.innerHTML = `<span class="who">agent</span>thinking about it...`;
  $("transcript").appendChild(node);
  scrollDown();
}

function clearThinking() {
  const node = $("thinking");
  if (node) node.remove();
}

function showTurn(turn) {
  state.lastTurn = turn;

  const node = $("turn-template").content.cloneNode(true);
  node.querySelector(".you .text").textContent = turn.user;
  node.querySelector(".agent .text").textContent = turn.reply;

  const meta = node.querySelector(".agent .meta");
  meta.innerHTML =
    `<span class="strategy">${turn.strategy}</span> | ` +
    `<span class="emotion">${turn.emotion}</span> | ` +
    `<span class="count">${turn.facts.length} facts | ` +
    `${turn.tokens} tok | ${turn.elapsed}s</span>`;

  $("transcript").appendChild(node);
  scrollDown();

  showFacts(turn.facts);
}

function showFacts(facts) {
  if (!facts || facts.length === 0) {
    $("facts").classList.add("hidden");
    $("fact-list").innerHTML = "";
    return;
  }

  $("facts").classList.remove("hidden");
  $("fact-list").innerHTML = facts
    .map(
      (fact) => `
      <div class="fact">
        <div class="uri">${fact.uri}</div>
        <div class="score">score ${(fact.score || 0).toFixed(3)} | L${fact.level}</div>
        <div class="abstract">${fact.abstract || ""}</div>
      </div>`
    )
    .join("");
}

function scrollDown() {
  const transcript = $("transcript");
  transcript.scrollTop = transcript.scrollHeight;
}

$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  send(null);
});

function send(verdict) {
  const text = $("message").value.trim();
  if (!text || !state.socket || state.socket.readyState !== WebSocket.OPEN) return;

  state.socket.send(
    JSON.stringify({ type: "message", text: text, agreed: verdict })
  );
  $("message").value = "";
  $("message").focus();
}

$("agree").addEventListener("click", () => {
  if (state.lastTurn) {
    state.socket.send(
      JSON.stringify({
        type: "message",
        text: "That is a fair point, I had not thought of it that way.",
        agreed: true,
      })
    );
    $("message").value = "";
  }
});

$("reject").addEventListener("click", () => {
  if (state.lastTurn) {
    state.socket.send(
      JSON.stringify({
        type: "message",
        text: "No, that is not right, prove it.",
        agreed: false,
      })
    );
    $("message").value = "";
  }
});
