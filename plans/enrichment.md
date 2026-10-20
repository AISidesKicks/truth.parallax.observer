# Source audit and enrichment plan

Status: audit done, the knowledge tier is still empty.

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

## The gap

`facts/knowledge/` has 8 planned directories and 0 files.

`plans/memory.md` splits the corpus in two:

- `resources/knowledge/` - the substance, source grounded, cited
- `resources/enrichment/` - the ammunition, catchphrases and claims

The retrieval plan in that same document searches both. One for the claim,
one for the ammo. Right now there is only ammo.

That matters for the experiment. The Spokesperson can quote a catchphrase but
not Rowbotham's actual treatise. The Fact Checker can say "that is false" but
cannot cite the geodesy paper. The Informant has nothing to inform with.

## Other findings

1. **Two empty quote categories.** `norse/quotes` and `spherical-earth/quotes`
   are 0 wisdoms. There are no seed files for them.

2. **Swapped frontmatter in `dataset/fictional/`.** 11 of 14 files have
   `target` and `category` the wrong way round:

   ```
   dataset/fictional/discworld/compleat-atlas.md   target=fictional  category=discworld
   dataset/fictional/discworld/discworld-geography.md target=discworld category=fictional
   ```

   The path is the only reliable signal. Anything that groups by frontmatter
   will mis-bucket those files.

3. **Two stray directories** at the root of `facts/enrichment/`:
   `nasa-photos-cgi/` and `nasa-photos-cgi-test/`. They come from
   `test_single_fact()` in `scripts/expand_enrichment.py`, which writes to
   `FACTS_DIR` instead of the category directory.

4. **The L2 texts are generated, not sourced.** They read well and they are
   good ammunition, but they carry hallucinations. In
   `flat-earth/misleading-facts/water-always-finds-its` the model credits the
   flat earth doctrine to Aristotle, who argued for a spherical earth. That
   is fine for a claim written to be persuasive, and not fine for the tier a
   fact checker is supposed to cite. This is the argument for building the
   knowledge tier from the raw text rather than from the model.

5. **`dataset/images/` is nearly empty.** Two files, four of five subfolders
   hold nothing. `scripts/download_images.py` exists but barely ran.

## What to build

### 1. A chunker for the raw sources

Split on headings, keep the source URL and the heading path in the front
matter, and write the chunk text verbatim. No model in the loop for the
content itself.

```
dataset/flat-earth/victorian/one-hundred-proofs.md
  -> facts/knowledge/flat-earth/victorian/one-hundred-proofs/<slug>/
       content.md      the text as written
       .abstract.md    the L0 essence, generated
       .overview.md    the L1 insight, generated
       .metadata.yaml  source_url, heading path, offsets
```

Verbatim content, generated summaries. The split mirrors what the
enrichment tier does, but the facts stay true because nobody rewrote them.

### 2. The same three tier names OpenViking wants

```
l0.abstract  ->  .abstract.md
l1.overview  ->  .overview.md
l2.content.md ->  content.md
```

Then `reindex(mode="vectors_only")` picks it up. No LLM call at index time.

### 3. Fix the frontmatter at the source

Rewrite `target` and `category` in the 14 `dataset/fictional/` files so the
values match the path. Cheap, and it removes a trap for the next script.

### 4. Fill the two empty quote categories

| Category | Source to mine |
|----------|----------------|
| `norse/quotes` | Edda verses, `dataset/fictional/norse/nine-worlds.md`, `norse-collector.md` |
| `spherical-earth/quotes` | `dataset/spherical-earth/scientific/`, scientists on geodesy |

### 5. Clean the stray directories

Move or remove `facts/enrichment/nasa-photos-cgi/` and
`facts/enrichment/nasa-photos-cgi-test/`, and point `test_single_fact()` at
the right directory so it stops writing to the root.

### 6. Make the image tier real, or drop it

Two options: finish the image download so the multimodal embedding model has
something to embed, or delete `dataset/images/` and the SigLIP part of the
plan. Half a feature is worse than none.

## Order of work

1. Frontmatter fix and stray directory cleanup. Cheap, unblocks everything.
2. Chunker for the raw sources, into `facts/knowledge/`.
3. Summary generation for the knowledge tier, reusing the existing tier
   prompts.
4. Quote seeds for the two empty categories.
5. Images, decide.

Step 3 is the only expensive one. 685 headings means a few hundred L0 and L1
pairs, roughly the same order of work as the 486 enrichment wisdoms that
already exist. On the llama.cpp chat server that is an evening, not a
weekend.
