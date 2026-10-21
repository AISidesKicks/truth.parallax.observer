# Source inventory

Status: 644 source files, 18 MB, four worldviews.

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

| Folder | Files | How |
|--------|-------|-----|
| `dataset/flat-earth/biblical` | 7 | docling |
| `dataset/flat-earth/vedic` | 7 | docling |
| `dataset/flat-earth/victorian` | 7 | docling, Gutenberg and LoC scans |
| `dataset/flat-earth/modern` | 122 | MediaWiki API |
| `dataset/spherical-earth/scientific` | 152 | docling and MediaWiki API |
| `dataset/fictional/discworld` | 257 | MediaWiki API |
| `dataset/fictional/norse` | 80 | MediaWiki API |

644 files, 611 of them pulled through the wiki API.

### The Discworld sources

| Wiki | What was pulled |
|------|-----------------|
| `wiki.lspace.org` | Category:Discworld geography, culture, concepts, characters. The canonical Discworld wiki. |
| `discworld.fandom.com` | Category:Ankh-Morpork locations, Category:Cities |

257 files. Ankh-Morpork, Lancre, Sto Lat, the Sto Plains, the Klopenburg sun,
the Edge, the Unseen University, the Patrician, the City Watch. The Discworld
geography is a whole continent with a coastline, and now the corpus has it.

### The Spherical Earth sources

| Wiki | What was pulled |
|------|-----------------|
| `en.wikipedia.org` | Category:Geodesy, Category:Surveying, and 54 explicit pages on the measurement of the Earth |
| `en.wikipedia.org` | Category:Flat Earth, the reference material for the fact checker |

The geodesy pages are the history of actually measuring the thing. Eratosthenes
in Alexandria, Picard in Picardy, Bouguer in Peru, La Perouse in the Pacific,
Laplace in Paris, Bessel in Hamburg, the Everest expedition. Eratosthenes did
it with a stick and a shadow in 200 BC and got it right to within a few
percent. Newton worked out the shape from the way a spinning thing behaves.
Then came the geodetic datum, the reference ellipsoid, the geoid, the
benchmark, the theodolite, the spirit level, and now satellite laser ranging
and very long baseline interferometry.

### The modern Flat Earth sources

| Wiki | What was pulled |
|------|-----------------|
| `wiki.tfes.org` | The Flat Earth Society wiki, 12 categories |
| `en.wikipedia.org` | Category:Flat Earth |

The Society wiki is the arguments in their own words, which is the point.
Gravity, Perspective, Parallax, Optics, Rotation and Revolution, Form and
Magnitude, General Physics, Historical Figures, Maps and Models, Celestial
Mechanics, Cosmology, Literature. Airy's Failure is a whole page about the
1871 experiment that is supposed to prove the Earth does not move.

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

## The tables

Eleven of the sources are mostly markdown tables, and some of them are a
single 300 KB line with the cells flattened together. The chunker now cuts
the tables on the cell boundary and repeats the header in every chunk, so a
table reads on its own:

```
| Title | Published | Transworld sub-series | ... |
|-------|-----------|----------------------|-----|
rows 11 to 20 of 42
| 11 | ... | 2007 | Wizards | ...
```

The wiki link markup goes with it, `[*The Colour of Magic*](/wiki/The_Colour_of_Magic)`
becomes `The Colour of Magic`.

Twenty one chunks were pure whitespace, the cells were lost in the
extraction. There is nothing in them, so they are dropped.

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

The `wiki.tfes.org` and `wiki.lspace.org` endpoints have no `/w/` in the
path. Wikipedia and Wikisource do. That difference cost one wasted run.

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
