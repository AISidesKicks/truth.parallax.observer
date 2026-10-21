# Tooling upgrade - llama.cpp + OpenViking 0.5

Status: configuration landed, runtime wiring still open.

## Why

Two things dragged the project down:

1. The memory layer was pinned to a February 2026 OpenViking (0.3.x) API that
   no longer exists. `SyncOpenViking(path=...)` is gone, the project is now a
   client/server split.
2. The model servers were Ollama plus Infinity. Two stacks, two model
   formats, and the models the code expected were not the models the
   container actually served.

Everything now runs locally on a single RTX 4070 (12 GB).

## The stack

| Piece | Before | After |
|-------|--------|-------|
| Chat | `ollama/ollama` + `granite4:tiny-h` | `ghcr.io/ggml-org/llama.cpp:server-cuda13` + `granite-4.0-h-tiny` |
| Embeddings | `michaelf34/infinity` + `modernbert-embed-base` | same llama.cpp server + `embeddinggemma-2` |
| Memory | OpenViking 0.3.x, hand rolled client | OpenViking 0.5.1.1 server + `openviking-sdk` |
| Env | conda | pixi (`prlx` workspace) |

Port numbers stay put so the app config barely moves:

| Service | Port | Container |
|---------|------|-----------|
| Chat and embeddings | 11433 | `prlx-llm` |
| OpenViking | 1933 | `prlx-viking` |
| Phoenix | 6006 | `prlx-phoenix` |
| App | 8668 | `prlx-app` / `prlx-dev` |

## One server for both models

llama.cpp v0.7.0 has a router mode. The server starts with no model and
loads the right one per request, based on the `model` field in the body.
`config/llama-models.ini` defines both presets, and `embeddings = true` is
set on the encoder preset only.

That gives one CUDA context instead of two. On a 12 GB card that is already
shared with another project, that is worth having.

If the router misbehaves, the fallback is the standalone `prlx-embed`
service, which is still in the compose file under the `embed` profile.

## What OpenViking 0.5.1.1 gives us

The project needs three things from the memory layer, and 0.5 has all three
as first class API:

- `find(query, target_uri=...)` scoped to one worldview directory
- `abstract()` / `overview()` / `read()` for the L0, L1 and L2 tiers
- sessions (`create_session`, `add_message`, `commit_session`) for the
  PersuChat belief state

`include_provenance` on a search result tells us exactly which fact the model
just used. That is the whole point of the experiment, so it matters more here
than anywhere else.

## How the corpus maps into OpenViking

The corpus on disk stays where it is. `facts/enrichment/<worldview>/<category>/<wisdom>/`
holds `l0.abstract`, `l1.overview` and `l2.content.md`.

OpenViking wants the same three tiers under different names:

```
facts/enrichment/flat-earth/misleading-facts/water-always-finds-its/
    l0.abstract      ->  .abstract.md
    l1.overview      ->  .overview.md
    l2.content.md    ->  content.md
```

Two things we learned the hard way:

- `add_resource` skips dot files, so `.abstract.md` and `.overview.md` never
  arrive through the normal import path.
- `add_resource` turns `content.md` into `content/content.md`, because it
  maps every file onto a directory.

So the migration writes the sidecars straight into the OpenViking workspace
on disk and then calls `reindex(mode="vectors_only")`. No LLM call, no
regenerated summaries, our pre-written L0 and L1 text survives untouched.

## Verified on this machine

| Check | Result |
|-------|--------|
| `openviking-server` 0.5.1.1 boots locally, no cloud, no API key | healthy |
| Import 486 wisdoms / 1458 files with `vectors_only` | 17 s, zero LLM calls |
| `reindex(vectors_only)` | 1458 records, 34 s |
| `find()` scoped per worldview | correct hits, 10-50 ms |
| `abstract()` / `overview()` | return our exact pre-generated text |
| Session memory API | works |

## The GPU constraint

The chat model is 4231 MB at Q4_K_M, the embedding server roughly 600 MB.
Another project on this host is holding 7.9 GB of the 12 GB card, so the two
llama.cpp servers only fit once that one is down.

| Quant | Size |
|-------|------|
| Q2_K | 2586 MB |
| Q3_K_M | 3353 MB |
| Q4_K_M | 4231 MB |
| Q8_0 | 7390 MB |

`LLAMA_MODEL_FILE` in `.env` picks the quant. Start smaller if the card is
busy.

## Open items

Done:

- [x] pixi environments and tasks
- [x] llama.cpp router serving both models
- [x] OpenViking 0.5.1.1 server, config validated against the real schema
- [x] the memory client rewritten on the SDK
- [x] the corpus seeded into the workspace by `scripts/migrate_to_viking.py`
- [x] the knowledge tier built from the raw sources
- [x] the seed parser fixed, the expansion ported to llama.cpp
- [x] `readme.md`, `docs/index.html` and the lab pages
- [x] the repo is under version control
- [x] the PersuChat slice, written from the BDD scenarios
- [x] the corpus seeded and indexed in a live OpenViking server
- [x] the app talking to the real model server and the real memory server

Still open:

1. **Fire Chat, the 3-way debate.** Slice 3 of the BDD. The moderator, the
   three personas and the stage machine.
2. **The lab view.** Slice 2. The reader should be able to open a fact and
   read where it came from.
3. **The app has no observability yet.** Phoenix is in the compose, the
   app does not send traces to it.
4. **The GPU monitor is not wired into the app.** `nvidia-ml-py` is a
   dependency and the bar asks for it, but nothing fills it in.
5. **The images.** `dataset/images/` still has two files in it.
6. **The chunks are at the edge.** The embedding model has a 2048 token
   context, so a chunk has to fit in about 6000 characters. 288 chunks were
   over that and could not be embedded until the chunk size came down.

## The host problem

The Docker runtime cannot reach the GPU on this machine. The nvidia kernel
module is 615.71.09 and the userspace libraries are 615.71.10, so the
container toolkit asks for a library that is not there:

```
failed to fulfil mount request: open
/usr/lib/x86_64-linux-gnu/libnvidia-gtk3.so.615.71.09: no such file or directory
```

That is a host problem, not a project problem. Until it is sorted the
llama.cpp server has to run natively, and there is a `native` pixi
environment for it:

```bash
pixi run -e native llama-server \
  --host 127.0.0.1 --port 11433 \
  --models-preset scratch/llama-models.local.ini \
  --models-max 2 --models-autoload
```

The conda-forge build is a bit older than the docker image, and it does not
know the `gemma-embedding2` architecture that EmbeddingGemma 2 uses. So the
native path runs EmbeddingGemma 300M instead. Everything else is the same,
including the router and the preset file.

The preset file is the one the compose uses, with the container paths
swapped for the host paths. That is the whole point of writing it down as a
file.


