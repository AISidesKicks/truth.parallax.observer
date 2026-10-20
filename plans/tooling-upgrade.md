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
| Embeddings | `michaelf34/infinity` + `modernbert-embed-base` | same llama.cpp image + `embeddinggemma-2` |
| Memory | OpenViking 0.3.x, hand rolled client | OpenViking 0.5.1.1 server + `openviking-sdk` |
| Env | conda | pixi (`prlx` workspace) |

Port numbers stay put so the app config barely moves:

| Service | Port | Container |
|---------|------|-----------|
| Chat | 11433 | `prlx-llm` |
| Embeddings | 7997 | `prlx-embed` |
| OpenViking | 1933 | `prlx-viking` |
| Phoenix | 6006 | `prlx-phoenix` |
| App | 8668 | `prlx-app` / `prlx-dev` |

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

1. `src/memory/viking_client.py` still hand rolls cosine similarity over
   `.embedding.json` files. Rewrite it on `openviking-sdk`.
2. `scripts/migrate_to_viking.py` does not exist yet. It seeds the workspace
   and calls `reindex`.
3. The app does not exist yet. `src/main.py`, `src/agentic/`, `src/gui/`.
4. `plans/bdd-app.md` is empty. Write the scenarios before the app code.
5. `readme.md` and `docs/index.html` are empty.
6. The repo is not under version control yet.
7. `src/dev.sh` still points at a conda environment. It should call pixi.
