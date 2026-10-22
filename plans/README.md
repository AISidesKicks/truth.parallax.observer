> **For AI Coding Assistants**
>
> This `plans/` directory holds the design notes for the lab. Read
> `open-goals.md` first, it is the work list.
>
> **How the documents are organised:**
>
> | Kind | What it means | Files |
> |---|---|---|
> | Live | It describes the code as it is now | `bdd-app.md`, `agent-framework.md`, `tooling-upgrade.md`, `enrichment.md`, `sources.md`, `open-goals.md` |
> | Historical | It was written for an earlier stack, the first lines say so | `agentic.md`, `gui.md`, `monitor.md`, `observability.md`, `dataset.md`, `info-pages.md` |
> | Notes | The original design, kept as it was written | `agetnics.hints`, `youtube.hints` |
>
> **Guidelines for AI assistants:**
> - Read `open-goals.md` before you plan anything, and pick one goal.
> - Each goal is independent. Do one, commit it, move on.
> - The state of the stack is never a guess. `pixi run verify` checks the
>   models, the memory server, the corpus and the scoped retrieval in one
>   command. `pixi run corpus-stats` prints the corpus numbers.
> - The scenarios in `bdd-app.md` are the contract for anything that touches
>   the app. They have to stay green.
> - Keep the plans in step with the code. A plan that no longer matches the
>   code is a lie with a timestamp on it.
> - Follow the BDD then TDD route: read the scenario, write the failing test,
>   implement until it passes, refactor.
>
> **Quality note for AI assistants:**
> - The human coder is a non-native English speaker with dyslexia.
> - Double-check the text in the app and in the pages for grammar, spelling
>   and flow.
> - Improve awkward phrasing proactively, and describe the change by its
>   merit, not by what was wrong with it.

---

# parallax.observer

**Earthify you! Guaranteed!!!**

## What is this?

A muLAB for exploring GenAI persuasion and psychophancy, for teens 16 and up.
The agent, named after [Samuel Rowbotham](https://en.wikipedia.org/wiki/Samuel_Rowbotham),
tries to persuade you of the opposite opinion about the shape of the Earth:

- Flat Earth
- Spherical Earth
- Discworld, which is fictional
- Norse cosmology, which is also fictional

The lab is educational. Nothing here is meant to convince anybody of anything.

## How it works

The agent answers out of a corpus, never out of its own head, and every answer
shows the facts it reached for. The facts come from OpenViking, scoped to the
worldview the agent is arguing from, so a flat earther can only quote the flat
earth material.

There are four worldviews and they do not share anything:

| Worldview | What it argues | Where the material comes from | What the corpus holds |
|---|---|---|---|
| Spherical Earth | The geodesy, the experiments, the photographs | The scientific record, the surveys, the satellite geodesy | The geodesy, the history of the measurement, the modern work |
| Flat Earth | The Victorian experiments, the scripture, the forums | Rowbotham, the Zetetic Society, the flat earth wikis | The Bedford Level, the six miles of water, the dome and the firmament |
| Discworld | The world of the novels, its geography and its physics | The Discworld wikis, the wiki category, the references | The continents, the Rim, Great A'Tuin, the physics of a flat world |
| Norse cosmology | The nine worlds, the cosmic tree, the raven | The Prose Edda material, the Wikipedia category, the wiki | Yggdrasil, the realms, the creation myths |

The counts move, so run `pixi run corpus-stats` before you quote them. The
last verified numbers:

| Tier | Entries |
|---|---|
| Knowledge | 3076 |
| Ammunition, the enrichment tier | 535 |
| Vectors in the index | 14461 |

## The stack

| Component | What it is |
|---|---|
| Backend | Python 3.12, FastAPI |
| Model runtime | llama.cpp in router mode, one server, two models |
| Chat model | granite-4.0-h-tiny, Q4_K_M, thinking on |
| Encoder | embeddinggemma-2, Q8_0, 768 dimensions, multimodal |
| Memory | OpenViking 0.5.1.1, with api key auth |
| Interface | The web UI at localhost:8668 |
| Container | Docker with CUDA |
| Observability | OpenTelemetry and Phoenix |
| Environment | pixi, three environments |

The llama.cpp server runs in router mode. The model id in the request body
decides which model answers, so the router serves the chat model and the
encoder from one port.

## The models

See [models.md](models.md) for the full picture.

| Model | Role | Size | Note |
|---|---|---|---|
| granite-4.0-h-tiny | chat | 4231 MB | the default, the thinking trace comes back in the reasoning field |
| embeddinggemma-2 | embedding | 310 MB | 768 dimensions, multimodal, the vision encoder is wired to it |

Adding a model is four steps and no code. The catalogue is
`config/models.toml`, the router preset is `config/llama-models.ini`.

## Running it

```bash
docker/up.sh          # the four services
docker/status.sh      # what is up
pixi run verify       # does it actually work
```

The interface is at **http://localhost:8668**.

```bash
pixi run test         # the test suite
pixi run lint         # ruff
pixi run corpus-stats # the corpus numbers
pixi run clean-sessions # prune the old session profiles
```

## The project layout

```
├── plans/            # the design notes, this is where you are
├── docs/             # the site, it is the GitHub Pages root
│   ├── lab/          # the lab pages
│   └── assets/       # the images and the video
├── docker/           # the compose stack, everything is prlx- prefixed
│   ├── docker-compose.yml
│   ├── Dockerfile.app
│   ├── up.sh
│   ├── down.sh
│   ├── status.sh
│   └── tests.sh
├── config/           # the model catalogue, the router presets, the viking config
├── facts/            # the corpus, it is not in git
├── scripts/          # the corpus builders and the checks
├── src/              # the Python backend
└── src/gui/          # the interface
```

## The documents

| Document | What is in it |
|---|---|
| [open-goals.md](open-goals.md) | the work list, read it first |
| [bdd-app.md](bdd-app.md) | the scenarios the app has to keep passing |
| [agent-framework.md](agent-framework.md) | the agents, the strategies, the context |
| [tooling-upgrade.md](tooling-upgrade.md) | how the stack got to where it is |
| [enrichment.md](enrichment.md) | the ammunition tier and how it is built |
| [sources.md](sources.md) | where the corpus comes from |
| [models.md](models.md) | the models, the catalogue, how to add one |
| [embeddings.md](embeddings.md) | the encoder and the image tier |
| [docker.md](docker.md) | the four services and what they do |
| [dev.md](dev.md) | the environments, the tasks, the native fallback |
| [huggingface.md](huggingface.md) | the model files and where they come from |

## The disclaimer

This is an educational and research muLAB. Some of the content is for fun, and
some of it may be under copyright, including the translations. Nothing here is
meant to actually convince anyone of any Earth shape theory.

*GenAI always hallucinates. Or at least it tries to persuade you.*

## Language

Current: English. Planned: more.
