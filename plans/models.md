# Models: the chat model, the encoder, and the catalogue

> The models parallax.observer runs, and the four steps to add one.

## How the models are served

One llama.cpp server, in router mode, serves everything. The model id in the
request body decides which model answers, so the chat model and the encoder
share a port and a CUDA context.

| From the host | From inside the network | What |
|---|---|---|
| `http://localhost:11433/v1` | `http://prlx-llm:8080/v1` | the router |

The router reads its presets from `config/llama-models.ini`. The name of a
section is the model id the router routes on, so a request has to carry
`"model": "granite-4.0-h-tiny"` and it lands on the right one.

```bash
# what the router serves
curl -s http://localhost:11433/v1/models | jq -r '.data[].id'

# a chat turn
curl -s http://localhost:11433/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "granite-4.0-h-tiny",
       "messages": [{"role": "user", "content": "Prove the Earth is round."}]}'

# a vector
curl -s http://localhost:11433/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "embeddinggemma-2", "input": "probe string"}'
```

The image is `ghcr.io/ggml-org/llama.cpp:server-cuda13`. The tag moves, so
the build number matters: the `gemma-embedding2` architecture that
EmbeddingGemma 2 needs landed in build 11455, and the `server-cuda-b4738`
line has the router removed. A pull of an older build answers
`unknown model architecture` and it looks like a broken model file.

## The models we run

| Model | Role | File | Quant | Size | Note |
|---|---|---|---|---|---|
| granite-4.0-h-tiny | chat | `granite-4.0-h-tiny-Q4_K_M.gguf` | Q4_K_M | 4231 MB | hybrid MoE, 128K context, thinking on |
| embeddinggemma-2 | embedding | `embeddinggemma-2-Q8_0.gguf` | Q8_0 | 310 MB | 768 dimensions, multimodal |

The chat model has thinking on. The reasoning trace comes back in the
`reasoning_content` field and the answer comes back in `content`, so the
interface can show the thinking separately or not at all.

The encoder needs its vision projector next to it,
`mmproj-embeddinggemma-2-Q8_0.gguf`. Without it the image tier does not
work, and with it the encoder still only answers with text vectors.

## The catalogue

`config/models.toml` is the catalogue. It is one section per model, and the
name of the section is the model id.

```toml
default = "granite-4.0-h-tiny"

["granite-4.0-h-tiny"]
file = "granite-4.0-h-tiny-Q4_K_M.gguf"
role = "chat"
reasoning = true
quant = "Q4_K_M"
size_mb = 4231
display = "Granite 4.0 H Tiny"
note = "Hybrid MoE, thinking mode. The default."
```

The section names are quoted. A bare key with a dot in it reads as a nested
table in TOML, and `granite-4.0-h-tiny` without the quotes becomes a table
called `granite-4`.

The `role` field separates the chat models from the encoders, so the app can
build the right set of clients out of one file. Only the chat models show up
in the picker.

## The per session model

The model is a property of the session, not a global setting. That is what
makes an A/B possible, and it is what a coding agent needs to load a model and
watch it argue.

```
src/config.py     catalogue_models(), chat_models(), default_model()
src/session.py    Session.model, and SessionStore.create(model=...)
src/main.py       ModelClients, one LLMClient per model id, made on first use
src/gui/          the picker on the setup form
```

The HTTP surface:

| Endpoint | What it does |
|---|---|
| `GET /api/models` | the catalogue, the picker is filled from it |
| `POST /api/session` | takes a `model`, a model the catalogue does not know falls back to the default |
| `GET /api/status` | the models that have a client loaded |

The orchestrator is made per model, and the Fire Chat gets the model of the
session that started it, so the moderator scores with the same model that
argued.

## The four steps to add a model

This is the whole extension point, and it is what a coding agent needs to
"find a model, load the model, defend the model".

1. Drop the GGUF into `.models/llama/`.
2. Add a `[section]` to `config/llama-models.ini`. The section name is the
   model id the router routes on.
3. Add an entry to `config/models.toml`.
4. Restart the router and the app.

No code changes. The app reads the catalogue at startup and makes a client
per model id on first use.

The check that keeps the three in step is in `pixi run verify`: every chat
model in the catalogue has to have a preset section and a file in
`.models/llama/`, or the verify fails.

## The two dialects

The router speaks the OpenAI dialect on `/v1`. The app speaks it too, through
`httpx2` in `src/llm.py`, and the streaming path reads the server sent events
by hand.

The dialect that matters is the one OpenViking speaks. The memory server
calls the encoder with an OpenAI shaped request and its own base url, which
is why `VIKING_EMBEDDING_BASE` points at the router in the compose file. The
app never embeds anything itself, the memory server does, and the app only
retrieves.

## The guardrails goal

There is a goal in `plans/open-goals.md` about running the same corpus
against a model whose safety training has been stripped, to show that
persuasion is a property of the setup and not of the model.

It is written and not built, and the reason is in the goal itself: the way
the guardrails come off is different for every model, so there is no recipe
to build once and reuse.

The model layer is what that goal needs. The catalogue is where the
uncensored build goes, the per session model is how the two runs stay
separate, and the argument ledger in the session is what the comparison reads.

## The corpus pipeline models

The corpus builders (`scripts/chunk_knowledge.py` and
`scripts/expand_enrichment.py`) talk to the same router, so they use the
chat model and nothing else. The pipeline used to run four models, one per
stage, and unload the ones it did not need. The router made that
unnecessary, and the GPU guardrails that came with it are still there, the
temperature pause at 80 degrees and the VRAM warning at 90 percent, along
with the per wisdom checkpoint and the resume.

## The files

| File | What it is |
|---|---|
| `config/models.toml` | the catalogue |
| `config/llama-models.ini` | the router presets |
| `.models/llama/` | the GGUF files, they are not in git |
| `src/config.py` | reading the catalogue |
| `src/llm.py` | the client, it takes the model in the constructor |
| `src/main.py` | the clients per model id |
| `docker/fetch-models.sh` | the downloads |
