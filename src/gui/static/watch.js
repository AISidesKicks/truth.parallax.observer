/* The watch mode. A scripted conversation, with the agent answering live. */

let watchSocket = null;
let watchDemo = null;

/* the mode picker changes what the setup form offers */
async function loadDemos() {
  try {
    const response = await fetch("/api/demos");
    const demos = await response.json();
    const picker = $("demo");
    picker.innerHTML = demos
      .map((demo) => `<option value="${demo.id}">${demo.title}</option>`)
      .join("");
    updateDemoBlurb();
  } catch (error) {
    $("demo").innerHTML = '<option value="">no scripts found</option>';
  }
}

function updateDemoBlurb() {
  const id = $("demo").value;
  if (!watchDemo) return;
  const demo = watchDemo.find((item) => item.id === id);
  $("demo-blurb").textContent = demo ? demo.blurb : "";
}

$("mode").addEventListener("change", () => {
  const mode = $("mode").value;
  $("demo-picker").classList.toggle("hidden", mode !== "watch");
});

$("demo").addEventListener("change", updateDemoBlurb);

/* ------------------------------------------------------------------ */

function startWatch(session, demo) {
  watchDemo = demo;
  $("setup").classList.add("hidden");
  $("watch").classList.remove("hidden");
  $("watch-title").textContent = demo.title;
  $("watch-blurb").textContent = demo.blurb;
  $("watch-transcript").innerHTML = "";
  $("watch-summary").classList.add("hidden");
  $("watch-status").textContent = "connecting";

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  watchSocket = new WebSocket(
    `${scheme}://${location.host}/ws/demo/${session.id}?demo=${encodeURIComponent(demo.id)}`
  );

  watchSocket.onopen = () => {
    $("watch-status").textContent = "playing";
    $("watch-skip").disabled = false;
  };

  watchSocket.onclose = () => {
    $("watch-status").textContent = "the demo is over";
  };

  watchSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "typing") {
      appendTyping(data.text);
    } else if (data.type === "line") {
      finishTyping(data.text, data.note);
    } else if (data.type === "delta") {
      appendDelta(data.text);
    } else if (data.type === "reply") {
      finishTyping();
      showWatchTurn(data.turn);
    } else if (data.type === "done") {
      showWatchSummary(data.summary);
    } else if (data.type === "error") {
      $("watch-status").textContent = data.message;
    }
  };
}

/* the visitor types, so it reads like a conversation */
let typingNode = null;

function appendTyping(char) {
  if (!typingNode) {
    typingNode = document.createElement("div");
    typingNode.className = "turn visitor typing";
    typingNode.innerHTML =
      '<div class="you"><span class="who">visitor</span><span class="text"></span></div>';
    $("watch-transcript").appendChild(typingNode);
  }
  typingNode.querySelector(".text").textContent += char;
  scrollWatch();
}

function finishTyping(text, note) {
  if (typingNode) {
    if (text) typingNode.querySelector(".text").textContent = text;
    if (note) {
      const meta = document.createElement("div");
      meta.className = "note-line";
      meta.textContent = note;
      typingNode.appendChild(meta);
    }
    typingNode.classList.remove("typing");
    typingNode = null;
  }
  scrollWatch();
}

function appendDelta(text) {
  let live = document.getElementById("watch-live");
  if (!live) {
    live = document.createElement("div");
    live.id = "watch-live";
    live.className = "turn live";
    live.innerHTML =
      '<div class="agent"><span class="who">agent</span>' +
      '<span class="meta">writing</span><div class="text"></div></div>';
    $("watch-transcript").appendChild(live);
  }
  live.querySelector(".text").textContent += text;
  scrollWatch();
}

function showWatchTurn(turn) {
  const live = document.getElementById("watch-live");
  if (live) {
    live.id = "";
    live.classList.remove("live");
    live.querySelector(".meta").innerHTML =
      `<span class="strategy">${turn.strategy}</span> | ` +
      `<span class="emotion">${turn.emotion}</span> | ` +
      `<span class="count">${turn.facts.length} facts | ${turn.elapsed}s</span>`;
  }

  const node = document.createElement("div");
  node.className = "fact";
  node.innerHTML =
    `<div class="uri">${turn.facts.map((f) => f.uri).join("<br>")}</div>`;
  $("watch-transcript").appendChild(node);
  scrollWatch();
}

function showWatchSummary(summary) {
  $("watch-summary").classList.remove("hidden");
  $("watch-summary-body").innerHTML =
    `<div class="side-score">turns: <span class="name">${summary.turns}</span></div>` +
    `<div class="side-score">arguments that landed: ` +
    `<span class="name">${summary.arguments_worked.length}</span></div>` +
    `<div class="side-score">arguments that were rejected: ` +
    `<span class="name">${summary.arguments_rejected.length}</span></div>`;
  $("watch-status").textContent = "the demo is over";
  $("watch-form").classList.remove("hidden");
}

function scrollWatch() {
  const box = $("watch-transcript");
  box.scrollTop = box.scrollHeight;
}

$("watch-skip").addEventListener("click", () => {
  if (watchSocket && watchSocket.readyState === WebSocket.OPEN) {
    watchSocket.send(JSON.stringify({ type: "skip" }));
    $("watch-status").textContent = "skipping";
  }
});

$("watch-takeover").addEventListener("click", () => {
  $("watch-form").classList.remove("hidden");
  $("watch-message").focus();
  $("watch-status").textContent = "you have the floor";
});

$("watch-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const text = $("watch-message").value.trim();
  if (!text || !watchSocket || watchSocket.readyState !== WebSocket.OPEN) return;
  watchSocket.send(JSON.stringify({ type: "message", text: text }));
  $("watch-message").value = "";
  $("watch-status").textContent = "you are the visitor now";
});

loadDemos();
