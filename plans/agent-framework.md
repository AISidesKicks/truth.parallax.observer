# Which agent framework

Decision: **PydanticAI.**

Status: settled and proven against our model server. `pydantic-ai-slim[openai]`
is installed, and the 35 existing tests still pass with it in the environment.

## The candidates

### VikingBot, inside `openviking[bot]`

Volcengine's own agent framework, shipped with the OpenViking server.

| | |
|---|---|
| Agent core | a 3362 line agent loop, on its own |
| Dependencies | 25 and counting: litellm, telegram, slack, discord, dingtalk, mcp, tavily, ddgs, langfuse, socketio, croniter, prompt-toolkit |
| Model access | litellm, so any OpenAI compatible endpoint works |
| OpenViking | first class, session context injection, experience memory, viking tools |
| Multi agent | none. `BotMode` is NORMAL, READONLY, DEBUG. No persona, no debate, no role. |

A very good bot framework. Not a debate framework, and not readable.

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
| Dependencies | anyio, httpx, packaging, pillow, pydantic, pygments, rich, textual, typer |
| Events | a typed event stream, and the contract everything meets on |
| Compaction | context accounting, manual and automatic |
| Thinking | off, minimal, low, medium, high, xhigh, max |
| Steering | the visitor can queue a message that interrupts the answer |
| Model access | OpenAI, Anthropic, Codex, OpenRouter, HF, and custom OpenAI compatible endpoints |
| Multi agent | none |

Their own words: "Tau is also meant to be read. It is a teaching project for
understanding the shape of a coding-agent system without starting from a giant
production codebase."

We installed it and ran it against our llama.cpp router. It works. 60 typed
events, the answer streamed intact, the router and the reasoning model
understood. It is a good piece of engineering.

### PydanticAI, `pydantic-ai-slim`

Pydantic's own agent framework. MIT.

| | |
|---|---|
| Dependencies | 8 core: anyio, genai-prices, griffelib, httpx2, opentelemetry-api, pydantic-graph, pydantic, typing-inspection. Plus the openai extra, which we already had. |
| Typed output | the point of it. A pydantic model as the output schema, validated, with retries on failure |
| Model access | any OpenAI compatible endpoint, through the openai SDK we already use |
| Streaming | yes, `run_stream` |
| Observability | OpenTelemetry in the core, and Phoenix is already in the stack |
| Injection | dependencies go in the run context, not through a tool loop |
| Graph | `pydantic-graph` is a core dependency, for a state machine when we want one |
| Tools | optional. An agent with an output type and a fixed prompt is a pipeline step, not a tool loop |

## Why not VikingBot

1. **It hides the machinery.** The lab exists so a reader can see which tactic
   was chosen, why, and which facts were used. To understand one turn in
   VikingBot you read 3362 lines of async machinery. That is the opposite of
   the point.
2. **The dependency weight is for a different product.** Five chat platforms,
   a search API, an MCP client and a tracing vendor, for a lab that is one
   web page. We would install litellm, a second HTTP stack and a second model
   abstraction, next to the OpenAI SDK we already use.
3. **It has no multi agent concept at all.** Fire Chat needs three personas,
   each with its own corpus scope, in a deterministic stage machine. That is
   the whole of slice 3 and VikingBot has no shape for it.

Its one real advantage, the OpenViking integration, is already covered by our
own client. And our client does the one thing that matters here and
VikingBot does not: scope a search to one worldview directory.

## Why not Tau

Tau was the favourite until the structured output question came up.

Tau's loop is tool driven. It asks the model to respond, and when the model
asks for a tool it runs the tool and asks again. Our turn is a fixed
pipeline:

```
read the visitor  ->  look in the corpus, scoped  ->  pick a tactic  ->  speak
```

The retrieval is deliberate. We scope the query to the worldview, we inject
exactly the material, and we pick the tactic from a rule set a reader can
inspect. If granite-4.0-h-tiny at 2B active parameters decided whether to
call `search_corpus`, retrieval would get worse and the lab premise would
break. Tau would be giving us a nicer way to do the thing we deliberately do
not want.

Tau also has one system prompt for the life of a harness, and our prompts
change every turn: persona, mood, tactic and material. We would rebuild the
harness on every turn anyway.

What Tau would have given us, and what we get elsewhere:

| From Tau | From PydanticAI instead |
|---|---|
| The provider layer, streaming, retries, thinking | the openai SDK, and PydanticAI on top of it |
| Context accounting and compaction | ours, it is 80 lines and it keeps the belief and the rejected arguments |
| The steering queue | ours to build, 30 lines |
| The event taxonomy | PydanticAI's event stream, and the websocket already speaks it |

## Why PydanticAI

It is the only one of the three that gives us the thing we actually needed
and does not take away the thing we actually want.

**The thing we needed.** The moderator has to score three sides of a debate
and return something the interface can render. That is a typed output, and
PydanticAI is a typed output library first. Proven on our 2B model:

```json
{
  "scores": [
    {"side": "Round Earth", "score": 8.0, "strongest_point": "...", "weakest_point": "..."},
    {"side": "Flat Earth", "score": 6.0, "strongest_point": "...", "weakest_point": "..."},
    {"side": "Disc on Elephants", "score": 2.0, "strongest_point": "...", "weakest_point": "..."}
  ],
  "winner": "Round Earth",
  "summary": "The debate was won decisively by the Round Earth side..."
}
```

That is a validated pydantic model, not a hopeful json.loads. The values are
in range, the shape is guaranteed, and a failure retries instead of reaching
the interface.

We have already paid for this lesson once. The enrichment pipeline parses
model output by hand, and its best effort json handling is the ugliest code
in the project. PydanticAI is the version of that we would have written.

**The thing we did not want to give up.** The tool loop is optional. An
agent with an output type and a fixed prompt is a pipeline step, and our
orchestrator stays a pipeline: retrieve, pick a tactic, speak. The model never
decides what to look up.

**What else comes with it.**

- Streaming, so the interface shows the answer arriving
- Usage accounting, so the monitoring bar is real
- OpenTelemetry in the core, and Phoenix is already in the stack
- The Viking client as a run context dependency, so the retrieval is
  available without being a tool
- `pydantic-graph` for the Fire Chat stage machine, if we want a formal one

## What we do

```
src/agentic/orchestrator.py   stays, it is the pipeline
src/llm.py                    becomes a PydanticAI agent factory
src/agentic/moderator.py      new, a typed agent that scores the sides
src/agentic/fire_chat.py      new, the stage machine
```

The Viking client is a run context dependency. The personas stay a dict. The
tactics stay a rule set. The reader still sees everything.

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
every build knows. 768 dimensions, multilingual, 310 MB.

If a llama.cpp release with `gemma-embedding2` lands, the swap is one line in
`config/llama-models.ini` and one re-index.
