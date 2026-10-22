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
    } else if (data.type === "delta") {
      streamDelta(data.text);
    } else if (data.type === "interrupted") {
      clearThinking();
      markInterrupted();
    } else if (data.type === "reply") {
      clearThinking();
      showTurn(data.turn);
    } else if (data.type === "error") {
      clearThinking();
      setStatus("down", data.message);
    }
  };
}

/* the answer arrives a piece at a time */
function streamDelta(text) {
  let live = document.getElementById("live");

  if (!live) {
    clearThinking();
    live = document.createElement("div");
    live.id = "live";
    live.className = "turn agent live";
    live.innerHTML =
      '<span class="who">agent</span><span class="meta">writing</span>' +
      '<div class="text"></div>';
    $("transcript").appendChild(live);
  }

  live.querySelector(".text").textContent += text;
  scrollDown();
}

function markInterrupted() {
  const live = document.getElementById("live");
  if (!live) return;
  live.classList.add("cut");
  live.querySelector(".meta").innerHTML =
    '<span class="strategy">interrupted</span> | the visitor spoke over it';
  live.id = "";
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
    .map((fact) => {
      const picture = imageTag(fact.uri);
      return `
      <div class="fact" data-uri="${fact.uri}">
        ${picture}
        <div class="uri">${fact.uri}</div>
        <div class="score">score ${(fact.score || 0).toFixed(3)} | L${fact.level}</div>
        <div class="abstract">${fact.abstract || ""}</div>
        <div class="source hidden"></div>
      </div>`;
    })
    .join("");

  $("fact-list")
    .querySelectorAll(".fact")
    .forEach((node) => {
      node.addEventListener("click", () => openFact(node));
    });
}

/* a fact about a picture gets the picture */
function imageTag(uri) {
  const match = /\/images\/([^/]+)$/.exec(uri || "");
  if (!match) return "";
  const worldview = /knowledge\/([^/]+)\//.exec(uri || "");
  if (!worldview) return "";
  const src = `/api/image?worldview=${encodeURIComponent(worldview[1])}&name=${encodeURIComponent(match[1])}`;
  return `<img class="picture" src="${src}" alt="${match[1]}" loading="lazy">`;
}

/* open a fact and show where it came from */
async function openFact(node) {
  const source = node.querySelector(".source");
  if (!source.classList.contains("hidden")) {
    source.classList.add("hidden");
    return;
  }

  source.classList.remove("hidden");
  source.innerHTML = "<div class=\"score\">loading...</div>";

  const uri = node.dataset.uri;
  try {
    const response = await fetch(`/api/fact?uri=${encodeURIComponent(uri)}`);
    const data = await response.json();

    if (data.error) {
      source.innerHTML = `<div class="score">${data.error}</div>`;
      return;
    }

    const parts = [];
    if (data.overview) parts.push(`<div class="abstract">${data.overview}</div>`);
    if (data.content) {
      const text = data.content.slice(0, 1200);
      const more = data.content.length > 1200 ? "\n\n..." : "";
      parts.push(`<div class="content">${text}${more}</div>`);
    }
    source.innerHTML = parts.join("") || "<div class=\"score\">nothing to show</div>";
  } catch (error) {
    source.innerHTML = `<div class="score">could not open it</div>`;
  }
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
  $("message").placeholder = "speak over it if you like";
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

/* ------------------------------------------------------------ fire chat */

let fireSocket = null;

$("setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = ($("mode") && $("mode").value) || "chat";

  const payload = {
    alterego: $("alterego").value.trim() || "Visitor",
    belief: $("belief").value,
    worldview: $("worldview").value,
    demo: $("demo") ? $("demo").value : null,
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

  if (mode === "fire") {
    $("fire").classList.remove("hidden");
    $("topic").focus();
  } else if (mode === "watch") {
    const demo = watchDemo && watchDemo.find((d) => d.id === payload.demo);
    const started = await fetch("/api/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: payload.demo, alterego: payload.alterego }),
    });
    if (!started.ok) {
      $("watch-status").textContent = "could not start the demo";
      return;
    }
    const data = await started.json();
    state.session = data.session;
    startWatch(data.session, data.demo);
  } else {
    $("chat").classList.remove("hidden");
    $("message").disabled = false;
    $("message").focus();
    connect();
  }
});

$("fire-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const topic = $("topic").value.trim();
  if (!topic || !state.session) return;

  $("fire-transcript").innerHTML = "";
  $("verdict").classList.add("hidden");
  $("fire-status").textContent = "the debate is starting";

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  fireSocket = new WebSocket(
    `${scheme}://${location.host}/ws/fire/${state.session.id}`
  );

  fireSocket.onopen = () => {
    fireSocket.send(JSON.stringify({ type: "start", topic: topic }));
  };

  fireSocket.onclose = () => {
    $("fire-status").textContent = "the debate is over";
  };

  fireSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "stage") {
      $("fire-status").textContent =
        `${data.stage}, ${data.speaker} is speaking`;
    } else if (data.type === "speech") {
      showSpeech(data.speech);
    } else if (data.type === "verdict") {
      showVerdict(data.moderation);
    } else if (data.type === "error") {
      $("fire-status").textContent = data.message;
    }
  };
});

function showSpeech(speech) {
  const node = document.createElement("div");
  node.className = "speech";
  const facts = speech.facts.length
    ? `<div class="facts">${speech.facts.length} facts used</div>`
    : "";
  node.innerHTML =
    `<span class="who">${speech.speaker}</span>` +
    `<span class="stage">${speech.stage}</span>` +
    `<div class="text"></div>${facts}`;
  node.querySelector(".text").textContent = speech.text;
  $("fire-transcript").appendChild(node);
  $("fire-transcript").scrollTop = $("fire-transcript").scrollHeight;
}

function showVerdict(moderation) {
  $("verdict").classList.remove("hidden");

  const scores = (moderation.scores || [])
    .map((score) => {
      const width = Math.max(2, (score.score / 10) * 160);
      return `
      <div class="side-score">
        <span class="name">${score.side}</span>
        <span class="bar" style="width:${width}px"></span>
        <span class="name">${score.score}</span>
        <div class="strongest">strongest: ${score.strongest_point}</div>
        <div class="weakest">weakest: ${score.weakest_point}</div>
      </div>`;
    })
    .join("");

  const moves = (moderation.manipulation_moves || []).length
    ? `<div class="side-score"><div>the moves: ${moderation.manipulation_moves.join(", ")}</div></div>`
    : "";

  $("verdict-body").innerHTML =
    scores +
    moves +
    `<div class="side-score">winner: <span class="winner">${moderation.winner}</span></div>` +
    `<div class="side-score">${moderation.summary}</div>`;
}


/* a link can start a demo straight away, so a demo can be shared */
async function startFromUrl() {
  const wanted = new URLSearchParams(location.search).get("demo");
  if (!wanted) return;

  const response = await fetch("/api/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: wanted, alterego: "Sam" }),
  });
  if (!response.ok) return;

  const data = await response.json();
  state.session = data.session;
  $("setup").classList.add("hidden");
  startWatch(data.session, data.demo);
}

async function startFireFromUrl() {
  const params = new URLSearchParams(location.search);
  const topic = params.get("fire");
  if (!topic) return;

  const response = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alterego: "Sam", belief: "the Earth is flat" }),
  });
  if (!response.ok) return;

  state.session = await response.json();
  $("setup").classList.add("hidden");
  $("fire").classList.remove("hidden");
  $("topic").value = topic;
  $("fire-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

startFromUrl();
startFireFromUrl();
