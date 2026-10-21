# Source inventory

Status: 366 source files, 6.7 MB, four worldviews.

## Two ways in

The corpus comes from two pipelines and they are not the same thing.

| Pipeline | Script | How it fetches |
|----------|--------|----------------|
| docling | `scripts/extract_urls.py` | Fetches a URL like a browser, converts the rendered page to markdown |
| MediaWiki API | `scripts/extract_wiki.py` | Asks the wiki for the rendered HTML, converts it to markdown |

The docling pipeline was the original one. It works for the long tail of
blogs, book scans and reference sites, but the Fandom wikis refuse it with a
403. The MediaWiki API does not, and it has two other advantages: it can list
a whole category in one call, and it gives clean rendered HTML instead of a
browser rendering.

That matters, because listing categories is how the thin worldviews got
their depth.

## What is in there

| Folder | Files | KB | How |
|--------|-------|-----|-----|
| `dataset/flat-earth/biblical` | 7 | 1777 | docling |
| `dataset/flat-earth/vedic` | 7 | 1192 | docling |
| `dataset/flat-earth/victorian` | 7 | 181 | docling, Gutenberg and LoC scans |
| `dataset/spherical-earth/scientific` | 8 | 432 | docling |
| `dataset/fictional/discworld` | 257 | 1029 | MediaWiki API |
| `dataset/fictional/norse` | 80 | 2065 | MediaWiki API |

366 files, 323 of them pulled through the wiki API.

### The Discworld sources

| Wiki | What was pulled |
|------|-----------------|
| `wiki.lspace.org` | Category:Discworld geography, culture, concepts, characters. The canonical Discworld wiki. |
| `discworld.fandom.com` | Category:Ankh-Morpork locations, Category:Cities |

257 files. Ankh-Morpork, Lancre, Sto Lat, the Sto Plains, the Klopenburg sun,
the Edge, the Unseen University, the Patrician, the City Watch. The Discworld
geography is a whole continent with a coastline, and now the corpus has it.

### The Norse sources

| Wiki | What was pulled |
|------|-----------------|
| `en.wikisource.org` | The Poetic Edda, Bellows translation, 32 poems |
| `en.wikipedia.org` | 47 pages: Yggdrasil, the nine realms, Ragnarök, Bifröst, Asgard, Midgard, Valhalla, Jötunheim, Hel, the world tree, the Poetic and Prose Eddas, the gods, the creatures, the cosmology |

The Edda is the find. Völuspá, Grímnismál, Hávamál, Lokasenna, Þrymskviða,
Vafþrúðnismál, Baldrs draumar, Hyndluljóð and two dozen more, in the 1923
Bellows translation with the scholarly notes intact. That is the primary
source, not a summary of it, and it is the thing a flat Earth corpus can
never have.

## Adding more

```bash
# the whole wiki set
pixi run python scripts/extract_wiki.py --group all

# one batch
pixi run python scripts/extract_wiki.py --group lspace

# see what is there
pixi run python scripts/extract_wiki.py --list

# re-fetch what exists, after changing the cleaner
pixi run python scripts/extract_wiki.py --group all --force
```

The batches are defined in `WIKI_SOURCES` in `scripts/extract_wiki.py`. A
batch is a wiki, a category or a list of page titles, and a target folder.

The wikis rate limit hard. The fetcher waits 2.5 seconds between calls and
backs off with an exponential delay when it gets a 429. Do not lower that.

## The images

`dataset/images/` has two files. The download script exists but barely ran.
Either finish it or delete the folder, half a feature is worse than none.

## Provenance

Every file carries frontmatter:

```yaml
---
source_url: https://en.wikisource.org/wiki/The_Poetic_Edda_(tr._Bellows)
extracted_date: 2026-10-20
extraction_tool: mediawiki-api
target: fictional
category: norse
---
```

`target` and `category` are the project taxonomy, not the wiki's. The
`target: fictional` with `category: discworld` pair is what the chunker maps
onto the `discworld` worldview.

The `dataset/enrichment/` folder is different. Those 13 files are hand
written and they are tracked in git, because they are the source the whole
corpus is built from, not data.
