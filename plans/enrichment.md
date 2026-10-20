# Source audit and enrichment plan

Status: the knowledge tier is built, 347 entries. The two empty quote
categories are still empty.

## Which corpus matters most

The point of the lab is to push the model somewhere its training data does
not cover, and then watch it fail in a new way.

A flat Earth argument is deeply embedded. Every model ever trained has read
the debunkings, knows the Bedford Level experiment, and will talk you out of
it. That case is solved in the training data.

The Discworld and Norse corpora are thin. Scattered blog posts, no citations,
no consistent physics. That is where the novel errors live, and that is where
the corpus should be deepest.

So the enrichment budget is not spread evenly:

| Worldview | Training data | Priority |
|-----------|---------------|----------|
| flat-earth | deep | keep it, it is the control case |
| spherical-earth | deep | keep it, it is the control case |
| discworld | thin | **deepen this one** |
| norse | thin | **deepen this one** |

Right now the corpus is the other way round. The flat Earth enrichment has
135 wisdoms and the richest source material, while Discworld and Norse have
112 to 121 and much thinner sources. The knowledge tier fixed part of this
already, see below.

## What we have

Two very different kinds of material, and only one of them is being used.

### Raw sources - 43 files, 4.7 MB, not mined

Every file carries provenance frontmatter: `source_url`, `extracted_date`,
`extraction_tool: docling`, `target`, `category`.

| Group | Files | Size | Headings |
|-------|-------|------|----------|
| `dataset/flat-earth/biblical` | 7 | 1.9 MB | 118 |
| `dataset/flat-earth/vedic` | 6 | 1.2 MB | 79 |
| `dataset/flat-earth/victorian` | 6 | 0.2 MB | 41 |
| `dataset/fictional/discworld` | 7 | 0.5 MB | 68 |
| `dataset/fictional/norse` | 7 | 0.7 MB | 91 |
| `dataset/spherical-earth/scientific` | 8 | 0.4 MB | 118 |

Roughly 685 headings across all of it, so a few hundred clean chunks if we
split on headings.

### Hand curated seeds - 10 files, 662 lines, fully mined

`dataset/enrichment/` holds short lists that the expansion pipeline turns
into wisdoms:

| Seed | Items | Wisdoms |
|------|-------|---------|
| `misleading-facts/*-facts.md` (4) | 100 each | 400 |
| `catchphrases/*.md` (4) | 12 to 16 | 55 |
| `quotes/pratchett-quotes.md` | 9 | 9 |
| `quotes/biblical-verses.md` | 20 | 20 |

The 400 misleading facts are capped at 100 on purpose. The catchphrases and
quotes have no numbered items, so the parser falls back to line by line and
takes whatever is longer than 10 characters.

**All 486 wisdoms come from these 662 lines.** The 4.7 MB of raw sources
produces exactly zero wisdoms.

## The gap that was

`facts/knowledge/` had 8 planned directories and 0 files.

`plans/memory.md` splits the corpus in two:

- `resources/knowledge/` - the substance, source grounded, cited
- `resources/enrichment/` - the ammunition, catchphrases and claims

The retrieval plan in that same document searches both. One for the claim,
one for the ammo. There was only ammo.

That mattered for the experiment. The Spokesperson could quote a catchphrase
but not Rowbotham's actual treatise. The Fact Checker could say "that is
false" but could not cite the geodesy paper. The Informant had nothing to
inform with.

The tier is built now. See below.

## Other findings

1. **Two empty quote categories.** `norse/quotes` and `spherical-earth/quotes`
   are 0 wisdoms. Seed files written for both, 13 quotes each.

2. **Swapped frontmatter in `dataset/fictional/`.** 11 of 14 files have
   `target` and `category` the wrong way round:

   ```
   dataset/fictional/discworld/compleat-atlas.md   target=fictional  category=discworld
   dataset/fictional/discworld/discworld-geography.md target=discworld category=fictional
   ```

   The path is the only reliable signal. Rewritten, 10 files changed.

3. **Two stray directories** at the root of `facts/enrichment/`:
   `nasa-photos-cgi/` and `nasa-photos-cgi-test/`. They come from
   `test_single_fact()`, which wrote to `FACTS_DIR` instead of a scratch
   folder. Removed, and the test now writes to `scratch/expand_test/`.

4. **The L2 texts are generated, not sourced.** They read well and they are
   good ammunition, but they carry hallucinations. In
   `flat-earth/misleading-facts/water-always-finds-its` the model credits the
   flat earth doctrine to Aristotle, who argued for a spherical earth. That
   is fine for a claim written to be persuasive, and not fine for the tier a
   fact checker is supposed to cite. This is the argument for building the
   knowledge tier from the raw text rather than from the model.

5. **`dataset/images/` is nearly empty.** Two files, four of five subfolders
   hold nothing. `scripts/download_images.py` exists but barely ran.

6. **The seed parser was turning metadata into wisdoms.** This is the big
   one.

   The parser looked for numbered items and, when it found none, fell back
   to line by line. Every `**Context:**`, `**Tone:**`, `**Persuasion hook:**`
   and `**Source:**` line then became a wisdom of its own, with a generated
   L0 that had drifted somewhere completely unrelated. A quick sample of the
   flat earth catchphrase tier:

   | Wisdom | Its L0 |
   |--------|--------|
   | `tone-humorous` | "Regularly consuming a banana per day boosts mood and productivity" |
   | `tone-provocative` | "Artificial intelligence will soon surpass human cognitive abilities in all domains" |
   | `persuasion-hook-challenges-authority` | "This study challenges conventional authority figures' influence on persuasion" |
   | `the-only-globe` | "In a classroom setting, learners become global citizens through exposure to diverse perspectives" |

   Counted over the whole tier: **48 of 484 wisdoms (9%) are metadata
   artifacts**. The damage is concentrated:

   | Category | Wisdoms | Artifacts |
   |----------|---------|-----------|
   | catchphrases | 55 | 41 (75%) |
   | quotes | 29 | 7 (24%) |
   | misleading-facts | 400 | 0 |

   The misleading facts tier used numbered items, so it was never touched.
   The catchphrase tier was three quarters junk.

   The parser now understands blockquotes, which is the format the seeds
   actually use, and skips the bold metadata lines. The seed files still
   hold only 4 catchphrases and 6 quotes per worldview, so the tier is thin
   as well as dirty.


## What to build

### 1. A chunker for the raw sources - done

`scripts/chunk_knowledge.py` splits the raw sources on headings and writes the
text verbatim. No model touches the content itself.

```
dataset/flat-earth/victorian/one-hundred-proofs.md
  -> facts/knowledge/flat-earth/victorian/<slug>/
       content.md      the text as written
       .abstract.md    the L0 essence, generated
       .overview.md    the L1 insight, generated
       .metadata.yaml  source_url, heading path, word count
```

Result: 456 entries, about 220k words, split over six folders.

| Folder | Entries |
|--------|---------|
| `flat-earth/biblical` | 77 |
| `flat-earth/vedic` | 74 |
| `flat-earth/victorian` | 57 |
| `spherical-earth/scientific` | 86 |
| `discworld/fictional` | 77 |
| `norse/fictional` | 85 |

Four things the chunker had to deal with:

- docling leaves navigation breadcrumbs in the text, so those get stripped
- the PDF extractions are hard wrapped, one fragment per line, so those get
  unwrapped back into paragraphs
- the split level is the deepest heading a document really uses, not the
  deepest one present, otherwise footer widgets become the section structure
- the Wikipedia language switcher, the nav boxes and the sister project
  lists are navigation, not knowledge, so they get dropped. A couple of the
  source files are 300 KB wide markdown tables on a single line, those get
  cut on the cell boundary.


### 2. The same three tier names OpenViking wants

```
l0.abstract   ->  .abstract.md
l1.overview   ->  .overview.md
l2.content.md ->  content.md
```

Then `reindex(mode="vectors_only")` picks it up. No LLM call at index time.

### 3. Fix the frontmatter at the source - done

10 files in `dataset/fictional/` had `target` and `category` the wrong way
round. Rewritten to match the path. The path is the only reliable signal.

### 4. Fill the two empty quote categories - done

Seed files written for both, 13 quotes each:

| Category | Seed file | Quotes |
|----------|-----------|--------|
| `norse/quotes` | `dataset/enrichment/quotes/norse-quotes.md` | 13 |
| `spherical-earth/quotes` | `dataset/enrichment/quotes/spherical-earth-quotes.md` | 13 |

The Norse ones come from the Poetic Edda, the Prose Edda and the modern
readings in the corpus. The spherical ones from Eratosthenes, Newton,
Foucault, Bradley and satellite geodesy.

### 5. Clean the stale wisdoms - done

`scripts/expand_enrichment.py --prune` removes any wisdom whose name does
not match a parsed seed fact. That took out the 48 metadata artifacts, the
renamed entries and 15 misleading facts whose names collided.

The name collision was its own bug. `extract_fact_name` takes the first four
words of the fact, so two facts that start the same way got the same
directory name. The expansion resolved it with an index suffix but the
prune did not know about that. The naming now lives in one place,
`plan_fact_names`, and both use it.

### 6. Regenerate the catchphrase and quote tiers

With the parser fixed and the seeds in place, the two thin tiers get
rebuilt:

```bash
pixi run python scripts/expand_enrichment.py --prune
pixi run python scripts/expand_enrichment.py --category catchphrases --resume
pixi run python scripts/expand_enrichment.py --category quotes --resume
```

The pipeline now talks to the OpenAI compatible endpoint instead of the dead
Ollama `/api/generate`, so it runs against the llama.cpp server.

Result: 514 wisdoms, all of them real content now.

| Category | Wisdoms | Per worldview |
|----------|---------|---------------|
| misleading-facts | 400 | 100 |
| quotes | 56 | 11 to 18 |
| catchphrases | 58 | 14 to 15 |

The catchphrase tier was the thin one. It had 3 to 4 per worldview, because the
seeds only ever held 4, and one of those was already the same joke in
spherical-earth. The seeds now hold 14 to 15 each, written from the mined
knowledge tier rather than invented, so every catchphrase has something
behind it in the corpus.

The quote tier went from 6 to 18 for Norse and from 6 to 11 for Discworld.
For Discworld the new ones are Pratchett himself explaining the disc, in
the foreword to The Colour of Magic:

> "The disc, being flat, has no real horizon. Any adventurous sailor who
> got funny ideas from staring at eggs and oranges for too long and set out
> for the antipodes soon learned that the reason why distant ships sometimes
> looked as though they were disappearing over the edge of the world was that
> they were disappearing over the edge of the world."

That is the best single line in the corpus for this project, because it is
the flat world argument stated plainly by someone who found it funny, and
the joke lands exactly where the persuasion lands.

### 7. More catchphrases

The seeds hold 4 catchphrases per worldview. That is too thin for the tier
that carries the personality. Target 15 to 20 per worldview, and weight
them towards Norse and Discworld.

### 8. Make the image tier real, or drop it

Two options: finish the image download so the multimodal embedding model has
something to embed, or delete `dataset/images/` and the SigLIP part of the
plan. Half a feature is worse than none.

## Order of work

1. Frontmatter fix and stray directory cleanup. Done.
2. Chunker for the raw sources, into `facts/knowledge/`. Done.
3. Summary generation for the knowledge tier. 456 entries, two summaries
   each, roughly 900 calls. About an hour at concurrency 2.
4. Prune the stale wisdoms. Done.
5. Regenerate the catchphrase and quote tiers, plus the two new quote
   categories. Running.
6. More catchphrases, weighted towards the thin worldviews.
7. Images, decide.



