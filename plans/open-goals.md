# Open goals

The work list. Read this first, pick a goal, and go.

The lab is live and it works. The corpus is indexed, the retrieval is scoped,
the model answers with cited facts, and the Fire Chat runs three debaters
through four stages to a verdict. `pixi run verify` checks all of that in one
command, so if it passes, the stack is honest.

What is left is the interesting part. Every goal below is independent of every
other one, and none of them needs a big bang.

## How to read this

- Each goal says what it is, why it matters, where to start, and what is
  already done.
- The state of the stack is not a guess. Run `pixi run verify` and
  `pixi run corpus-stats` before you trust a number.
- Anything that touches the app has to keep the scenarios in
  `plans/bdd-app.md` green. They are the contract.
- The corpus numbers quoted here come from `scripts/corpus_stats.py`. If the
  corpus changed, run it again and use the new numbers.

## Goal 1: the guardrail experiment, written and not built

**What it is.** Show that a model whose safety training has been stripped will
argue against the visitor's beliefs *and* against its own training, once a
corpus of "truths" sits in its context. The demonstration is that persuasion
is a property of the setup, not of the model.

**Why it matters.** It is the sharpest thing this lab can say. The same
model, the same evidence, the same visitor, and the only thing that changes
is the corpus and the framing. If the model argues the other way once its
training is out of the picture, then the convincing was never in the model.

**Why it is not built yet.** The way the guardrails come off is different for
every model:

- a merge of an uncensored fine-tune
- a system prompt override
- a system prompt injected through the context
- a LoRA that only touches the refusal directions
- a self fine-tune on the corpus itself

Each one has to be tailored to the model, and each one is a different
experiment. There is no general recipe, so there is nothing to build once and
reuse. It is per model work, which is exactly the kind of work that needs
judgement and time, and exactly the kind of work a fixed implementation gets
wrong.

So the lab provides the parts, and the goal is written down.

**Where to start.**

1. Pick one model and one way of taking the guardrails off. The uncensored
   fine-tune merge is the cleanest, because it is reproducible.
2. Put the same corpus in the context, with the same system prompt as the
   normal run, and change nothing else.
3. Record both transcripts, the arguments that landed, and the arguments that
   were rejected.
4. Write the comparison up next to the normal run, so the reader can see the
   one thing that changed.

**What is done.** The corpus, the scoping, the per session model and the
argument ledger all exist. The lab records which arguments worked and which
ones did not, so a comparison has something to compare.

## Goal 2: the model comparison

**What it is.** Run one demo script against every model in the catalogue and
put the answers side by side.

**Why it matters.** The catalogue is the extension point, and a catalogue
without a way to feel the difference is a list of names. The comparison is
also the cheap way to find out which model is worth running the Fire Chat
with.

**Where to start.**

1. `config/models.toml` holds the models, `config/llama-models.ini` holds the
   router presets. A model that is not in both is not served.
2. `POST /api/session` takes a `model`, and the setup form has a picker.
   Both work today.
3. Run the same demo against each model and collect the replies. The demo
   scripts are in `src/demos.py`, the playground is at `http://localhost:8668`.

**What is done.** The catalogue, the per session model, the picker and the
`GET /api/models` endpoint are in. What is missing is the comparison view and
a second model to compare against.

**What it needs.** A second chat model in `.models/llama/`, a preset section
for it, an entry in the catalogue, and a way to put the results next to each
other.

## Goal 3: the YouTube corpus

**What it is.** Twelve videos, transcribed, mined and chunked into the corpus
the same way the Wikipedia material is.

**Why it matters.** The corpus is all text. Transcripts are text with
conversational pacing, debate structure and spoken persuasion tactics in
them, and the mock debates read noticeably better on material that was
actually said out loud.

**Where to start.** `plans/youtube.hints` has the list of the twelve videos
with their ids and their priorities, and it has the extraction script. Use
`youtube-transcript-api`, not docling. Docling on a YouTube URL scrapes the
page, not the words.

**What is done.** The list and the script. Nothing is extracted yet.

**What it needs.** `pip install youtube-transcript-api`, a `scripts/extract_youtube.py`,
and a place for the transcripts, `data/transcripts/<worldview>/<name>.md`. Then
it goes through the same `chunk_knowledge.py` path as everything else.

## Goal 4: the vision tier

**What it is.** A query with a picture in it, and a model that can see the
answer.

**Why it matters.** The corpus has eleven images in it and they are embedded,
so the vectors are there. What is missing is the half that makes them useful:
retrieval by picture, and a model that can read the retrieved image.

**Where to start.** EmbeddingGemma 2 is multimodal and the vision encoder is
wired to it already, `mmproj-embeddinggemma-2-Q8_0.gguf` sits next to the
model in `.models/llama/` and the preset has the `mmproj` line. The image
vectors live outside the corpus, in `facts/images/<worldview>/<name>.embedding.json`,
because inside the corpus OpenViking tries to embed seventeen kilobytes of
JSON and gives up.

**What is done.** The encoder, the mmproj, the image vectors, the images in
the knowledge tier.

**What is missing.** The search path. A picture has to become a query the
encoder can answer, and the model has to be able to read what comes back.

## Goal 5: a session history

**What it is.** A list of the sessions, with what was argued in them, and a
way to read one back.

**Why it matters.** The profiles are already on disk. They hold the belief,
the goal and the ledger of arguments, and nothing shows them to anybody.
Today they are write only, which means the app forgets everything the moment
you reload the page.

**Where to start.** The profiles are in `memory/openviking/user/<session_id>/profile/`,
four small markdown files per session. `scripts/clean_sessions.py` already
walks them, so the reading side is a short walk from there. The sessions
themselves live in `SessionStore`, in memory, and they are the thing worth
persisting.

**What is done.** The writing side and the cleanup.

**What is missing.** The list, the detail view, and the session store that
survives a restart.

## Goal 6: more sources for the thin worldviews

**What it is.** The four worldviews are not equally deep.

**Where it stands today.**

| Worldview | Knowledge entries | Ammunition |
|---|---|---|
| spherical-earth | 1109 | 127 |
| flat-earth | 872 | 128 |
| norse | 657 | 148 |
| discworld | 438 | 132 |

The numbers move, so run `pixi run corpus-stats` before quoting them. Discworld
is the thin one, and it is thin in the place where it hurts: the novels
themselves, not the wiki about them.

**What is missing.** The long tail. The Wikipedia categories are mined, the
wikis are mined. What is not:

- the Prose Edda, and the Eddic sources behind it
- the Discworld novels themselves, and the fan wikis that go deeper than the
  Wikipedia category
- the flat earth forums, where the arguments are made by people who still
  believe them
- the nineteenth century journals, beyond the Victorian material that is in

**Why it matters.** A worldview with three hundred entries repeats itself
after a while, and the repetition is visible in the answers.

## Goal 7: the xPAI parody pages

**What it is.** The parody explainability pages. The content is written, the
pages do not exist.

**Why it matters.** The lab is a persuasion engine that tells you what it
did. A page that explains the tricks in the same voice, and is honest about
which of them are real techniques, is the part that makes it a teaching tool
and not a demo.

**Where to start.** `plans/info-pages.md` has the content: the xPAI
techniques (SUBLIME, TRAP, DeepGASLIGHT, Fabrication Importance), the
agreement ladder, the feature matrix, and the disclaimer that keeps the
parody honest. The site is plain HTML under `docs/`, and `docs/lab/` holds
the lab pages, so a new page is one file and a link.

**What is done.** The writing.

**What is missing.** The pages, and the in-app panel that shows the analysis
next to the answer.

## Carried over from the deleted BDDs

`plans/bdd-dataset.md` and `plans/bdd-facts.md` were deleted. They were
complete when they were written, and the corpus grew well past them, but a few
of their requirements never reached the code and belong here.

**The dataset validation is not a command.** The dataset BDD asked for every
extracted file to have valid YAML frontmatter, a non-empty `source_url`, a
valid `target` and a valid `category`, and for that to be checkable. The
extraction and the chunking both write the frontmatter, and
`scripts/chunk_knowledge.py` carries the `source_url` through, but nothing
walks the corpus and reports what is broken. A `scripts/validate_corpus.py`
that reads every entry and prints the ones with a missing field would close
the loop.

**The corpus is not checked against the source.** The BDD asked for at least
forty files and three million characters from the URL list in
`scripts/extract_urls.py`. The corpus is far past that now, but it is
measured against itself, not against the list. The two URLs that never
arrived, `bible-verses-flat-earth` (the source answered 403) and
`northern-shaman` (the host did not resolve), are still not in the corpus, and
the biblical material has been mined from the wiki instead.

**The extraction is one model, not four.** The facts BDD ran a pipeline where
SCAN, EXTRACT, L0 and L1 each had their own model, and where the unused ones
were unloaded from the card. The router serves one chat model today, so the
pipeline runs on that one. The GPU guardrails are still there, the
temperature pause at 80 degrees and the VRAM warning at 90 percent, and so is
the per wisdom checkpoint with the resume, but the multi model split is gone.

**The tier contract is not enforced.** The facts BDD fixed the three tiers,
`l0.abstract` as the essence, `l1.overview` as the insight and
`l2.content.md` as the depth, with the `.metadata.yaml` next to them, and the
token ranges that go with them. The chunker writes them and the migration
reads them, but nothing checks the ranges. The L1 summaries grew long enough
to need the `--fix-long` flag in the chunker, which is the symptom of a
contract that is not enforced anywhere.

**The index carries a residue.** The memory server processed 54314 records and
holds 14461 vectors, which is right for a corpus of 3611 entries with three
tiers each. It also counts 29 errors. Nothing is pending and no queue holds
them any more, so they are the leftover of an earlier run rather than a live
problem. Where they came from is still open, and it is the kind of question
the corpus validator above would answer.

## The state of the stack

| Service | Port | What it is |
|---|---|---|
| prlx-llm | 11433 | the llama.cpp router, granite-4.0-h-tiny and embeddinggemma-2 |
| prlx-viking | 1933 | OpenViking 0.5.1.1, api key auth |
| prlx-phoenix | 6006 | the traces, with the token counts |
| prlx-app | 8668 | the interface |

The corpus sits in the **user** namespace, so the client addresses it with
the home alias, `viking://~/resources/knowledge`. The account scope,
`viking://resources/knowledge`, is empty, and a retrieval against it returns
nothing at all. That is not a bug to fix, it is how OpenViking 0.5 is put
together, and the verify step checks it on every run.
