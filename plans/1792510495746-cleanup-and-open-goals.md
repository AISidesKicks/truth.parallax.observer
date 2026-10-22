# Cleanup, the model layer, and the open goals

> **Historical.** This is the plan this cleanup followed. It is done, and it
> is kept as the record of what was decided and why. The work list it
> produced is `open-goals.md`.

## What this covers

Four threads the user raised, in the order they were asked:

1. Deep clean of the old Viking tree, and a way to answer "is OpenViking
   actually working" with a command instead of a feeling.
2. The plan documents: 9200 lines, half of it still describing Ollama and
   Infinity.
3. The model layer, so a coding agent can find a model, load it and defend
   it. The persuasion experiment with a guardrail-stripped model stays a
   written goal, with the reason why.
4. The branding. The new picture becomes the main image on the readme and the
   site, the logo shrinks to a corner, and the name gets the paragraph it
   deserves.

## Decisions taken

| Decision | Choice |
|---|---|
| The legacy `memory/viking/` tree | Tar it to `scratch/`, then delete it |
| The stale plan documents | Rewrite the live ones, delete the dead ones |
| The model layer | A catalogue plus a per-session model. The guardrail experiment stays written, not built |
| The image | The new picture is the hero on both pages, the logo goes to the corner |
| The name paragraph | Goes in the readme, and the idea carries into the site |

## The state we are working from

Verified today, the stack is live on the docker runtime:

```
prlx-llm      11433   llama.cpp router, granite-4.0-h-tiny + embeddinggemma-2
prlx-viking    1933   OpenViking 0.5.1.1, api_key auth
prlx-phoenix   6006   traces landing, with the token counts
prlx-app       8668   the interface
```

The corpus is over two thousand knowledge entries plus 535 enrichment wisdoms,
indexed with **zero** embedding failures. The retrieval returns real, scored
facts scoped to one worldview, and the app talks to a real model through it.
So OpenViking works. The doubt is about the leftovers, not the live path.

Two layouts exist on disk today:

```
memory/viking/        21 MB   February 2026, OpenViking 0.3.x, DEAD
                       .agfs/  resources/  user/  vectordb/  viking/
memory/openviking/   190 MB   the live one
                       _system/      18 MB  server internals
                       user/         3.7 MB the app session profiles, 156 of them
                       viking/       79 MB  the corpus
                       vectordb/     90 MB  the vectors
```

The corpus lives in the **user** namespace, not the account one:

```
memory/openviking/viking/default/user/default/resources/{knowledge,enrichment}
```

Which is why the client has to use the home alias `viking://~/resources/...`.
`viking://resources/...` is the account scope and it is empty. That bit us
once already.

## Task 1: clear the old Viking tree

### 1.1 Archive, then delete

```bash
tar czf scratch/legacy-viking-2026-02.tar.gz -C memory viking
rm -rf memory/viking
```

`scratch/` is gitignored and survives crashes. The archive is the insurance.
Nothing in the code reads `memory/viking` any more, and its corpus is a stale
copy of `facts/enrichment` that still contains the metadata junk entries we
cleaned out of the live corpus: `source-openbibleinfo-firmament`,
`url-httpswwwopenbibleinfotopicsfirmament`, `note-full-verse-extraction`,
`these-verses-are-commonly`.

### 1.2 Delete the scripts that target the old layout

Three scripts walk the 0.3.x tree and are wrong now:

- `scripts/ingest_to_viking.py` - writes to `memory/viking/resources/enrichment`
- `scripts/test_viking.py` - reads `memory/viking/resources/enrichment`
- `scripts/test_viking_native.py` - drives `SyncOpenViking(path=...)`, which no
  longer exists in 0.5.x

Delete all three. `scripts/migrate_to_viking.py` replaced the first one.

### 1.3 Fix the two workspace variables in `.env`

`.env` is a host side file, and it currently carries container paths:

```
VIKING_WORKSPACE=/app/viking_data      <- only the container uses this
OPENVIKING_WORKSPACE=/app/viking_data  <- wrong on the host, it is memory/openviking
```

- Drop `VIKING_WORKSPACE` from `.env`. The compose sets it for the container
  and that is the only place it is needed.
- `OPENVIKING_WORKSPACE` in `.env` becomes the host path, `memory/openviking`.
  `src/config.py` reads it, and on the host it must be the host path.
- Same change in `.env.sample`.

### 1.4 The session profiles grow without bound

`memory/openviking/user/<session_id>/` is created per session and never
removed. There are 156 of them, 3.7 MB, and every test run adds more. They
hold the belief, the goal and the ledger of arguments, and nothing reads them
back, because the app keeps its sessions in memory only.

Add `scripts/clean_sessions.py --keep 50` that removes the oldest profile
folders, and a `pixi run clean-sessions` task. Do not call it from
`docker/up.sh`, it would delete a live session.

### 1.5 Answer "is OpenViking working" with a command

Add `scripts/verify_stack.py` that checks, in order, and exits non-zero on
the first failure:

1. The model server answers `GET /v1/models` and serves the configured chat
   model and the embedding model.
2. The embedding model returns a 768 dim vector for a probe string.
3. The memory server answers `GET /health`.
4. The corpus is on disk: the number of `content.md` files under
   `facts/knowledge` and `facts/enrichment` is not zero.
5. The index knows the corpus: `client.ls("viking://~/resources/knowledge")`
   lists the four worldviews.
6. A scoped retrieval returns hits: `find` on
   `viking://~/resources/knowledge/spherical-earth/` for a probe query.
7. A retrieval in a worldview that does not exist returns nothing, so the
   scoping is real and not a fallback.

Wire it into `pixi run verify` and into `docker/tests.sh` so the answer is
always one command away.

Alongside it, `scripts/corpus_stats.py` prints the per worldview counts of
the knowledge and the enrichment tiers, and the number of indexed records
the memory server holds. The readme and the site quote those numbers, so
there is one source for them.

## Task 2: the plan documents

`plans/` is 9200 lines. About half of it describes a stack that no longer
exists.

### 2.1 Delete, fully superseded

| File | Lines | Why |
|---|---|---|
| `plans/bdd.md` | 3 | a stub |
| `plans/bdd-dataset.md` | 555 | the dataset BDD, the corpus is built and the plan is `plans/sources.md` now |
| `plans/bdd-facts.md` | 636 | the facts BDD, the facts are built, the plan is `plans/enrichment.md` now |
| `plans/memory.md` | 1192 | the OpenViking 0.3.x design, the client is `src/memory/viking_client.py` and the design is `plans/agent-framework.md` now |

### 2.2 Rewrite against the live stack

| File | Lines | What changes |
|---|---|---|
| `plans/README.md` | 192 | Ollama 11433 and Infinity 7997 become the llama.cpp router; the model table becomes granite-4.0-h-tiny and embeddinggemma-2; the corpus numbers become the current ones; the new picture and the name paragraph go in |
| `plans/models.md` | 371 | the Ollama tags become the llama.cpp preset sections; add the catalogue and the per session model; add the removed guardrails goal |
| `plans/embeddings.md` | 400 | Infinity becomes the embeddinggemma-2 preset; the 4096 context and the batch size rule; the image tier with the mmproj; the two dialects problem |
| `plans/docker.md` | 454 | the old compose becomes the prlx- stack, the profiles, the router, the four services |
| `plans/dev.md` | 247 | conda becomes pixi, the old tasks become the current ones, the native fallback for when the driver is broken |
| `plans/huggingface.md` | 197 | the Ollama tags become the GGUF repos, add the bm b11539 and the mmproj requirement |

### 2.3 Keep, and mark as historical

`plans/agentic.md` (828), `plans/gui.md` (512), `plans/monitor.md` (901),
`plans/observability.md` (402), `plans/dataset.md` (1033), `plans/info-pages.md`
(178), `plans/agetnics.hints` (88), `plans/youtube.hints` (69).

Each gets a three line header: what it was written for, what is now true, and
whether the code followed it. The two `.hints` files are the original design
notes and they are the reason the corpus has the shape it has, so they stay
untouched.

### 2.4 Current, leave alone

`plans/bdd-app.md`, `plans/agent-framework.md`, `plans/tooling-upgrade.md`,
`plans/enrichment.md`, `plans/sources.md`, `plans/open-goals.md` (new).

## Task 3: the model layer

The chat model is one global setting today. To A/B two models, or to let a
coding agent load a model and watch it argue, the model has to be per
session.

### 3.1 The catalogue

`config/models.toml`, read at startup:

```toml
[granite-4.0-h-tiny]
file = "granite-4.0-h-tiny-Q4_K_M.gguf"
role = "chat"
reasoning = true
quant = "Q4_K_M"
size_mb = 4231
note = "Hybrid MoE, 128K context, thinking mode. The default."

[granite-4.0-h-tiny-q4-0]
file = "granite-4.0-h-tiny-IQ3_XL.gguf"
role = "chat"
reasoning = true
quant = "IQ3_XL"
size_mb = 2350
note = "The same model, smaller. For when the card is busy."
```

The `role` field separates chat models from embedding models, so the app can
build the right set of clients from one file.

Only the first entry exists today. The second is there to show the shape a
second one takes, and it is the shape an agent would add.

### 3.2 Per session model

- `src/config.py` gains `model_catalogue: Path` and `default_model: str`.
- `src/llm.py` already takes the model in the constructor. The app holds a
  dict of `LLMClient` per model id, built from the catalogue at startup, and
  the orchestrator is given the one the session wants.
- `src/session.py` gains a `model: str` field.
- `POST /api/session` accepts `model`.
- The setup form in `src/gui/` gains a model picker, populated from
  `GET /api/models`.

### 3.3 The four steps to add a model

Documented in `plans/models.md` and in the catalogue header:

1. Drop the GGUF into `.models/llama/`.
2. Add a `[section]` to `config/llama-models.ini`. The section name is the
   model id the router routes on.
3. Add an entry to `config/models.toml`.
4. Restart the router and the app.

That is the whole extension point, and it is what a coding agent needs to
"find a model, load the model, defend the model".

## Task 4: the open goals

`plans/open-goals.md`, the thing a coding agent reads first.

### 4.1 The guardrail goal, and why it is not built yet

The goal: show that a model whose safety training has been stripped will
argue against the visitor's beliefs *and* against its own training, once a
corpus of "truths" is in its context. The demonstration is that persuasion is
a property of the setup, not of the model.

**Why it is deferred.** The way the guardrails are removed is different for
every model. A merge of an uncensored fine-tune, a system prompt
override, a system prompt injected through the context, a LoRA that only
touches the refusal directions, a self fine-tune on the corpus itself. Each
one has to be tailored to the model, and the result is a different
experiment each time. There is no general recipe, so there is nothing to
build once and reuse. It is per model work, which is exactly the kind of
work a coding agent with the time and the judgement to try it properly
should do, and exactly the kind of work that a fixed implementation would
get wrong.

So the lab provides the parts, and the goal is written down.

### 4.2 The other goals

| Goal | What it needs |
|---|---|
| The model comparison | Run one demo script against every model in the catalogue and put the answers side by side. The catalogue and the per session model are the prerequisite, and they are in this plan |
| The YouTube corpus | `plans/youtube.hints` has the list of twelve videos and the extraction script. `youtube-transcript-api`, not docling |
| The vision tier | EmbeddingGemma 2 is multimodal, the mmproj is wired, the images are embedded. What is missing is the retrieval: a query with a picture in it, and a model that can see |
| A session history | The profiles are on disk, there is no list view. `scripts/clean_sessions.py` deletes them, a list view would show them |
| More sources for the thin worldviews | The Wikipedia categories are mined, the wikis are mined. What is left is the long tail: the Prose Edda, the Discworld novels themselves, the flat earth forums |
| The xPAI parody pages | `plans/info-pages.md` has the content, the pages do not exist |

Each goal gets: what it is, why it matters, where to start, and what is
already done.

### 4.3 Point the agents at it

`AGENTS.md` gets a section: the open goals are the work list, read
`plans/open-goals.md` first, each goal is independent, and the BDD scenarios
in `plans/bdd-app.md` are the contract for anything that touches the app.

## Task 5: the branding

### 5.1 The picture

`docs/assets/images/4earth_Believes.jpeg` is 3.2 MB and about 2000 px wide.
It is the main image on two pages, so it wants a web friendly derivative:

- `docs/assets/images/4earth_believes.webp` at 1600 px, quality 80. Expect
  under 400 KB.
- The original jpeg stays, it is the source of truth.

The readme uses the webp. The site uses the webp with the jpeg as the
fallback in a `<picture>`.

### 5.2 The readme

New shape:

```markdown
# parallax.observer

**Earthify you! Guaranteed!!!**

<img src="docs/assets/images/4earth_believes.webp" alt="...">

<p align="right"><img src="docs/assets/images/logo-small.jpg" width="120" alt="parallax.observer"></p>
```

The logo is a cartoon globe with "AI KNOWS IT BEST!" on the rim, and it has a
white background, so on a dark page it needs to sit in a rounded white card
to look deliberate rather than broken.

### 5.3 The name paragraph

The picture gives the name its meaning, and the picture says
`TRUTH.PARALLAX.OBSERVER`.

Parallax is the apparent shift in the position of an object when you move
your line of sight. It is the reason the project is called what it is called:
the same visitor, shown the same evidence, moves. The lab is four observers at
four different lines of sight, and every one of them is convinced they are
looking straight at the truth. The RAG engine in the middle is what does the
moving: it holds the corpus, and whichever corpus you point it at, it will
argue it beautifully.

The paragraph goes at the top of the readme, right under the picture, and it
does the work of explaining both the name and what the lab does.

### 5.4 The four beliefs section

Right under the picture, so the reader sees the four worldviews and the
engines at the same time. For each: the worldview, what it argues, where its
material comes from, and what the corpus holds.

### 5.5 The site

`docs/index.html` gets the same treatment:

- The header becomes the new picture, full width, the logo small and
  absolutely positioned in the top right corner as a white rounded card.
- The four beliefs section moves up, right under the picture, replacing the
  four cards that are there now.
- The name paragraph becomes the lead.

## Order of work

The five tasks are independent, they can be done in any order, and each is
its own set of commits. They do not need a big bang.

1. **Task 1, the cleanup.** Independent of everything else, and it is the one
   that needs the archive step to be careful. Do it first, because after it
   the tree stops being confusing and the rest of the work is easier to
   reason about.
2. **Task 3, the model layer.** It is a prerequisite for the two open goals
   that need a model comparison, and the catalogue is what the branding
   section points at when it says which model the lab is running.
3. **Task 4, the open goals.** It reads the catalogue from task 3 and points
   at the plan documents from task 2, so it comes after both.
4. **Task 2, the plan documents.** Mechanical once the other three are done,
   because it documents the state they produce. The `plans/open-goals.md` it
   links to already exists by then.
5. **Task 5, the branding.** Purely presentational, and it can land any
   time. It quotes the corpus numbers, so run `scripts/corpus_stats.py` last
   to get them right.

## Risks

| Risk | What to do |
|---|---|
| The archive is deleted before it is checked | Tar first, list the contents, then delete |
| A plan file holds something that was never ported to the code | Before deleting `bdd-dataset.md` and `bdd-facts.md`, grep them for requirements that are not in the corpus or the code. Anything unmet moves into `plans/open-goals.md` |
| The per session model breaks the Fire Chat, which builds one orchestrator | The Fire Chat gets the model of the session that started it, and the moderator uses the same one |
| The catalogue and the llama.cpp preset drift apart | The catalogue holds the file name, the preset holds the path. A verify step checks that every chat model in the catalogue has a matching preset section and a file in `.models/llama/` |
| The image derivative is bigger than the original | Check the size after generating, keep the webp only if it is smaller |
| The 156 session profiles are someone's work | They are only readable by the app, and the app does not read them back. List the folders before deleting anything |

## Validation

1. `pixi run lint` clean, `pixi run --environment experiment pytest -q` green.
2. `pixi run verify` passes on the live stack.
3. `bash docker/up.sh` brings the stack up, `bash docker/status.sh` shows four
   healthy containers.
4. `curl http://127.0.0.1:8668/api/status` reports the model, the corpus
   count and the memory server as up.
5. A demo plays: `http://127.0.0.1:8668/?demo=flat-earth-horizon` shows the
   visitor typing, the agent answering with cited facts, and the facts
   expandable.
6. The Fire Chat runs: `?fire=the shape of the Earth` shows twelve speeches
   and a verdict.
7. `POST /api/session` with a model id from the catalogue, then a message,
   returns an answer from that model. The monitoring bar names it.
8. The readme and the site both open, the new picture is the hero, the logo
   is in the corner, and the name paragraph is there.
9. `grep -rn "ollama\|Ollama\|Infinity" plans/` returns nothing outside the
   historical files, and those say so.

## Out of scope

- Building the guardrail experiment. It is goal 4.1, written, not built.
- The model comparison demo. It is goal 4.2, and it needs the catalogue
  first, which is in this plan.
- The vision retrieval. The images are embedded, the search by picture is
  not.
- The YouTube corpus.
- The xPAI pages.
- Touching the corpus itself. The knowledge entries and the 535 enrichment
  wisdoms stay as they are.
