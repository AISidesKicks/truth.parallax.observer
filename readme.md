# parallax.observer

**Earthify you! Guaranteed!!!**

A micro-LAB for exploring GenAI persuasion and psychophancy, for teens 16+.

The AI agent (named after [Samuel Rowbotham](https://en.wikipedia.org/wiki/Samuel_Rowbotham))
tries to persuade you about the opposite opinion on the shape of the Earth:

- Flat Earth 🗺️
- Spherical Earth 🌐
- Discworld, the fictional one 🐢🐘🌍
- Norse cosmology, the mythological one 🌲🔨

## Why the weird ones

A flat Earth argument is deeply embedded in the training data. The model has
read every debunking article, it knows the Bedford Level experiment inside
out, and it will politely and correctly talk you out of it. That is a solved
problem.

Push the model into Norse cosmology or a Pratchett disc and the ground
disappears. The training data is thin, the facts are strange, and the errors
get strange with them. That is where the interesting failures live, and that
is the part worth showing.

The lab exists to make those failures visible. Every retrieval is observable,
every fact the agent used is traceable back to a source, and every wrong
claim it makes is on the record.

## What is in the box

- **Persuasive AI agent** - Granite models served by llama.cpp, CUDA
- **Four bodies of world knowledge** - one flat Earth corpus with Victorian,
  biblical and Vedic sources, one scientific corpus, one Discworld corpus,
  one Norse corpus. 2262 source grounded entries and 535 ammunition entries.
- **Two tiers of knowledge** - `knowledge` holds the source text verbatim and
  can be cited, `enrichment` holds the ammunition: catchphrases, quotes and
  misleading claims
- **Observable retrieval** - you see exactly which fact the model reached for
- **Session memory** - the agent remembers what worked on you
- **Terminal style web UI** at `http://localhost:8668`

## Content philosophy

> **We are NOT an encyclopedic RAG.**

Quality over quantity. We do not need 100,000 facts for immersion.

| What we want | What we do not want |
|--------------|---------------------|
| Punchy catchphrases | Long encyclopedic articles |
| Memorable fun facts | Dry academic content |
| Humor with purpose | Boring data dumps |
| One concept per file | Overlapping information |

The goal is a **persuasion playground**, not a Wikipedia clone.

## Tech stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12 |
| Environment | pixi (`prlx` workspace) |
| LLM runtime | llama.cpp router server, Docker, CUDA |
| Embeddings | same llama.cpp server, EmbeddingGemma 2 |
| Quantization | GGUF, Q4_K_M for chat, Q8_0 for embeddings |
| Memory | OpenViking 0.5 server + `openviking-sdk` |
| Vector store | LanceDB, local backend |
| UI | Web based terminal UI |
| Containers | Docker, everything prefixed `prlx-` |
| Observability | OpenTelemetry + Phoenix |
| GPU monitoring | `nvidia-ml-py` |

### Models

| Role | Model | Repo | Size |
|------|-------|------|------|
| Chat | granite-4.0-h-tiny | `ibm-granite/granite-4.0-h-tiny-GGUF` | 4231 MB (Q4_K_M) |
| Embeddings | embeddinggemma-2 | `ggml-org/embeddinggemma-2-GGUF` | 310 MB (Q8_0) |

Both live in one llama.cpp server. It runs in router mode, so the request
body decides which model answers. That is one CUDA context instead of two,
which matters on a 12 GB card shared with other projects. The presets are in
[`config/llama-models.ini`](config/llama-models.ini).

EmbeddingGemma 2 is multimodal and outputs 768 dimensions with MRL truncation
down to 128.

### Ports

| Service | Port | Container |
|---------|------|-----------|
| Chat and embeddings | 11433 | `prlx-llm` |
| OpenViking | 1933 | `prlx-viking` |
| Phoenix | 6006 | `prlx-phoenix` |
| App | 8668 | `prlx-app` |

## Quick start

```bash
# 1. install the python environment
pixi install

# 2. fetch the GGUF models (about 4.5 GB)
docker/fetch-models.sh

# 3. start the stack
docker/up.sh

# 4. check that everything came up
docker/status.sh
```

Development mode with hot reload:

```bash
docker/up.sh dev
```

The app runs at **http://localhost:8668**.

### Working on the corpus

```bash
# rebuild the knowledge tier from the raw sources
pixi run python scripts/chunk_knowledge.py

# and generate the L0 and L1 summaries
pixi run python scripts/chunk_knowledge.py --summarize --resume
```

## Project structure

```
├── readme.md        # this file
├── plans/           # technical planning documents
├── didactic/        # educational methodology
├── docs/            # GitHub Pages site (docs.parallax.observer)
├── lab/             # lab instructions
├── dataset/         # raw extracted sources
├── facts/           # generated wisdoms, two tiers
│   ├── knowledge/   # source text, verbatim, citable
│   └── enrichment/  # catchphrases, quotes, misleading claims
├── config/          # runtime configuration
├── docker/          # the local stack
├── scripts/         # corpus and ingestion pipelines
└── src/             # python backend
```

### Key planning documents

- [tooling-upgrade.md](plans/tooling-upgrade.md) - the llama.cpp and
  OpenViking 0.5 upgrade, with the local verification results
- [enrichment.md](plans/enrichment.md) - source audit and the knowledge tier
- [models.md](plans/models.md) - LLM and VLM models
- [embeddings.md](plans/embeddings.md) - embedding model setup
- [docker.md](plans/docker.md) - container architecture
- [observability.md](plans/observability.md) - Phoenix and OpenTelemetry
- [monitor.md](plans/monitor.md) - GPU monitoring
- [gui.md](plans/gui.md) - the terminal style web interface
- [agentic.md](plans/agentic.md) - the multi-agent debate system
- [memory.md](plans/memory.md) - the OpenViking memory design
- [info-pages.md](plans/info-pages.md) - the xPAI parody pages

## License

See [LICENSE](LICENSE).

## Disclaimer

This is an educational and research micro-LAB. Some content is for FUN and may
be subject to copyright. Not intended to actually convince anyone of any
Earth shape theory.

*GenAI ALWAYS hallucinates. Or at least tries to persuade you. 😄*
