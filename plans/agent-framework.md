# Which agent framework

Decision: **take Tau's provider layer, keep our own orchestrator, do not use
VikingBot.**

Status: settled, `tau-ai` is installed and proven against our model server.

## The three candidates

### VikingBot, inside `openviking[bot]`

Volcengine's own agent framework, shipped with the OpenViking server.

| | |
|---|---|
| Agent core | a 3362 line agent loop, on its own |
| Dependencies | 25 and counting: litellm, telegram, slack, discord, dingtalk, mcp, tavily, ddgs, langfuse, socketio, croniter, prompt-toolkit |
| Model access | litellm, so any OpenAI compatible endpoint works |
| OpenViking | first class, session context injection, experience memory, viking tools |
| Multi agent | none. `BotMode` is NORMAL, READONLY, DEBUG. No persona, no debate, no role. |

It is a very good bot framework. It is not a debate framework, and it is not
readable.

### Tau, `huggingface/tau`

A Python port of Pi's minimalist coding agent harness. MIT, 9 dependencies.

```
tau_ai      provider and model streaming layer
tau_agent   the portable brain: messages, tools, events, loop, harness, sessions
tau_coding  the CLI app: resources, skills, commands, TUI, provider config
```

| | |
|---|---|
| Agent core | 1548 lines in total, the brain itself about 1100 |
| Dependencies | anyio, httpx, packaging, pillow, pydantic, pygments, rich, textual, typer. Four we already have. |
| Events | a typed event stream, and the contract everything meets on |
| Compaction | context accounting, manual and automatic |
| Thinking | off, minimal, low, medium, high, xhigh, max |
| Steering | the visitor can queue a message that interrupts the answer |
| Model access | OpenAI, Anthropic, Codex, OpenRouter, HF, and custom OpenAI compatible endpoints including local models |
| Multi agent | none |

Their own words: "Tau is also meant to be read. It is a teaching project for
understanding the shape of a coding-agent system without starting from a giant
production codebase."

### What we have

A hand written orchestrator in `src/agentic/`. Roughly 400 lines, no
dependencies, 35 tests, and it is written from the BDD scenarios.

## Why not VikingBot

1. **It hides the machinery.** The lab exists so a reader can see which tactic
   was chosen, why, and which facts were used. To understand one turn in
   VikingBot you read 3362 lines of async machinery. That is the opposite of
   the point.
2. **The dependency weight is for a different product.** Five chat platforms,
   a search API, an MCP client and a tracing vendor, for a lab that is one
   web page. We would install litellm, which pulls a second HTTP stack and a
   second model abstraction, next to the OpenAI SDK we already use.
3. **It has no multi agent concept at all.** Fire Chat needs three personas,
   each with its own corpus scope, in a deterministic stage machine. That is
   the whole of slice 3 and VikingBot does not have a shape for it.

Its one real advantage, the OpenViking integration, is already covered by our
own client. And our client does the one thing that matters here and
VikingBot does not: scope a search to one worldview directory.

## Why not the Tau harness as the brain

Tau's loop is tool driven. It asks the model to respond, and when the model
asks for a tool it runs the tool and asks again.

Our turn is a fixed pipeline:

```
read the visitor  ->  look in the corpus, scoped  ->  pick a tactic  ->  speak
```

The retrieval is deliberate. We scope the query to the worldview, we inject
exactly the material, and we pick the tactic from a rule set that a reader can
inspect. The strategy selection is a rule, not a coin flip.

If the model decided whether to call `search_corpus`, granite-4.0-h-tiny at
2B active parameters would retrieve worse, and the lab premise would break.
Tau would be giving us a nicer way to do the thing we deliberately do not
want.

There is a second reason. Our prompts are built per turn. The persona, the
mood, the tactic and the material all change. Tau's harness takes one system
prompt for its life, so we would rebuild the harness on every turn anyway,
which throws away the thing it was supposed to give us.

## What we take from Tau

### The provider layer, whole

`tau_ai` replaces `src/llm.py`. It is strictly more than what we wrote:

- streaming, so the interface can show the answer arriving instead of waiting
- retries with backoff and readable HTTP errors
- thinking mode handling, which our reasoning models need
- usage accounting per call, for the monitoring bar

Four of the nine dependencies we already have. Proven against our llama.cpp
router with granite-4.0-h-tiny, 60 typed events, streamed answer intact.

### The steering queue

Tau's `steer()` and `follow_up()` let a message arrive while the agent is
still answering. For a persuasion lab that is a real feature. The visitor
can cut the agent off mid-sentence, and the agent has to cope with being
interrupted.

It is about thirty lines in our orchestrator, and the idea is worth taking
whether or not we use the package.

### The event taxonomy

Message start, text delta, thinking delta, tool call, done. Our websocket
already streams a small version of this. Tau's names are a good model for
the full one.

## What we do not take

The harness, the loop, the tools, the sessions, the TUI, the CLI.

## The plan

1. `src/llm.py` becomes a thin wrapper over `tau_ai.OpenAICompatibleProvider`
2. The orchestrator keeps the fixed pipeline, and gets a steering queue
3. The websocket speaks the Tau event taxonomy
4. Fire Chat is built on the orchestrator, not on a framework

## The finding about the models

Neither released llama.cpp build knows the `gemma-embedding2` architecture
that EmbeddingGemma 2 uses:

```
llama_model_load: error loading model: unknown model architecture: 'gemma-embedding2'
```

That is true of `server-cuda13` build 10423, of `server-cuda-b4738`, and of
the conda-forge build. The official GGUF exists, the architecture is just
newer than every published binary.

So we use EmbeddingGemma 300M, the `gemma-embedding` architecture, which
every build knows. 768 dimensions, multilingual, 310 MB, and it embeds our
corpus in about four minutes.

If a llama.cpp release with `gemma-embedding2` lands, the swap is one line in
`config/llama-models.ini` and one re-index.
