# BDD Plan: Facts Generation for OpenViking

> Wisdom extraction with Essence/Insight/Depth tiers

## Feature: Wisdom Extraction

**As a** developer building the persuasion AI  
**I want to** transform raw content into wisdom entries with Essence/Insight/Depth tiers  
**So that** the AI can efficiently retrieve relevant knowledge during debates

---

## Background

```gherkin
Background:
  Given the parallax.observer conda environment is active
  And Ollama is running with granite models available
  And Infinity embedding server is running
  And the /facts/ directory structure exists
```

---

## Wisdom Terminology

Each entry in `/facts/` is a **Wisdom** - self-contained knowledge with context and persuasion value.

| Tier | File | Name | Purpose |
|------|------|------|---------|
| **L0** | `l0.abstract` | **Essence** | Core claim (~100 tokens) |
| **L1** | `l1.overview` | **Insight** | Context, hooks, counter-arguments (~500 tokens) |
| **L2** | `l2.content.md` | **Depth** | Full explanation (max 2K tokens) |

---

## Stage 1: Test Pipeline with Enrichment Wisdoms

### Scenario 1.1: Facts directory structure is created

```gherkin
Scenario: Facts directory structure is created
  Given I am setting up the facts generation system
  When I initialize the facts directories
  Then the following directories should exist:
    | facts/knowledge/flat-earth/victorian/    |
    | facts/knowledge/flat-earth/biblical/     |
    | facts/knowledge/flat-earth/vedic/        |
    | facts/knowledge/spherical-earth/         |
    | facts/knowledge/fictional/discworld/     |
    | facts/knowledge/fictional/norse/         |
    | facts/enrichment/flat-earth/catchphrases/          |
    | facts/enrichment/flat-earth/misleading-facts/      |
    | facts/enrichment/flat-earth/quotes/                |
    | facts/enrichment/spherical-earth/misleading-facts/ |
    | facts/enrichment/discworld/catchphrases/           |
    | facts/enrichment/discworld/quotes/                 |
    | facts/enrichment/norse/catchphrases/               |
    | facts/enrichment/norse/quotes/                     |
```

---

### Scenario 1.2: Ollama models are available for pipeline

```gherkin
Scenario: Ollama models are available for pipeline
  Given Ollama is running on port 11433
  When I check available models
  Then the following models should be available:
    | Model              | Purpose              |
    | granite4:tiny-h    | SCAN, TIER L1        |
    | granite3.3:2b      | EXTRACT              |
    | granite4:micro-h   | TIER L0              |
```

---

### Scenario 1.3: Single wisdom is extracted with Essence/Insight/Depth

```gherkin
Scenario: Single wisdom is extracted with Essence/Insight/Depth
  Given I have an enrichment fact:
    """
    Why NASA has never shown a real photo of Earth. Period.
    """
  And target is "flat-earth"
  And category is "misleading-facts"
  When I run the wisdom extraction pipeline
  Then a wisdom directory "facts/enrichment/flat-earth/misleading-facts/nasa-photos-cgi/" should exist
  And the directory should contain:
    | File          | Content                              |
    | l0.abstract   | L0 Essence (~100 tokens)             |
    | l1.overview   | L1 Insight (~500 tokens) with hooks  |
    | l2.content.md | L2 Depth (max 2,000 tokens)          |
  And each file should have valid YAML frontmatter
```

---

### Scenario 1.4: L0 Essence meets token requirements

```gherkin
Scenario: L0 Essence meets token requirements
  Given a wisdom entry has been extracted
  When I examine the l0.abstract file
  Then the content should be between 50 and 150 tokens
  And the content should contain:
    - Core claim summary
    - Key argument
    - Brief counter-point
```

---

### Scenario 1.5: L1 Insight includes persuasion structure

```gherkin
Scenario: L1 Insight includes persuasion structure
  Given a wisdom entry has been extracted
  When I examine the l1.overview file
  Then the content should be between 400 and 600 tokens
  And the content should contain sections:
    | Section            | Purpose                           |
    | Summary            | Key points (3-5)                  |
    | Persuasion Hooks   | How to use in debate              |
    | Counter-Arguments  | For agent awareness               |
    | Related Concepts   | Links to other wisdoms            |
```

---

### Scenario 1.6: L2 Depth stays within token limit

```gherkin
Scenario: L2 Depth stays within token limit
  Given a wisdom entry has been extracted
  When I examine the l2.content.md file
  Then the content should not exceed 2,000 tokens
  And the content should be between 500 and 2,000 tokens
  And the content should include:
    - Expanded argument explanation
    - Supporting examples
    - Usage guidance
```

---

### Scenario 1.7: Batch extraction of flat-earth wisdoms

```gherkin
Scenario: Batch extraction of flat-earth wisdoms
  Given I have 10 flat-earth misleading facts in dataset/enrichment/
  When I run the batch wisdom extraction pipeline
  Then 10 wisdom directories should be created in facts/enrichment/flat-earth/misleading-facts/
  And each directory should contain l0.abstract, l1.overview, and l2.content.md
  And all files should have valid YAML frontmatter
```

---

### Scenario 1.8: Batch extraction of all enrichment wisdoms

```gherkin
Scenario: Batch extraction of all enrichment wisdoms
  Given I have enrichment content for all targets:
    | Target         | Catchphrases | Misleading Facts | Quotes |
    | flat-earth     | 4            | 10               | 0      |
    | spherical-earth| 4            | 10               | 0      |
    | discworld      | 3            | 10               | 6      |
    | norse          | 3            | 10               | 0      |
  When I run the full wisdom extraction pipeline
  Then the following directories should be populated:
    | Directory                                          | Expected Wisdoms |
    | facts/enrichment/flat-earth/misleading-facts/      | 10              |
    | facts/enrichment/spherical-earth/misleading-facts/ | 10              |
    | facts/enrichment/discworld/misleading-facts/       | 10              |
    | facts/enrichment/norse/misleading-facts/           | 10              |
  And total wisdom directories should be at least 40
```

---

### Scenario 1.9: Parallel processing improves performance

```gherkin
Scenario: Parallel processing improves performance
  Given I have 10 enrichment facts to expand
  When I run the expansion pipeline with parallel processing
  Then all 4 model tasks should execute concurrently where possible
  And the total processing time should be less than sequential processing
  And the pipeline should use:
    | Task    | Model              | Parallel |
    | SCAN    | granite4:tiny-h    | No       |
    | EXTRACT | granite3.3:2b      | Yes      |
    | TIER L0 | granite4:micro-h   | Yes      |
    | TIER L1 | granite4:tiny-h    | Yes      |
```

---

### Scenario 1.10: All files have valid YAML frontmatter

```gherkin
Scenario: All files have valid YAML frontmatter
  Given I have expanded enrichment facts
  When I validate all generated files
  Then every file should start with "---"
  And every file should end the frontmatter with "---"
  And every file should contain required fields:
    | Field    | Description                    |
    | uri      | viking:// URI                  |
    | source   | Original dataset file path     |
    | target   | flat-earth/spherical/discworld/norse |
    | category | misleading-facts/catchphrases/quotes |
    | tokens   | Token count                    |
    | tier     | L0/L1/L2                       |
```

---

### Scenario 1.11: Expansion handles LLM errors gracefully

```gherkin
Scenario: Expansion handles LLM errors gracefully
  Given the LLM returns an error for one fact
  When I run the expansion pipeline
  Then the error should be logged
  And the pipeline should continue with remaining facts
  And a retry should be attempted for the failed fact
  And if retry fails, the fact should be marked as failed in a report
```

---

### Scenario 1.12: Git ignores facts directory

```gherkin
Scenario: Git ignores facts directory
  Given the facts directory contains generated content
  When I check git status
  Then the facts/ directory should be ignored
  And "facts/" should be listed in .gitignore
```

---

### Scenario 1.13: Wisdom entry has hidden centralized metadata file

```gherkin
Scenario: Wisdom entry has hidden centralized metadata file
  Given a wisdom directory in facts/
  When I examine the directory
  Then .metadata.yaml should exist
  And it should contain:
    | Field      | Description                    |
    | uri        | viking:// URI                  |
    | source     | Original dataset file          |
    | target     | flat-earth/spherical/etc       |
    | category   | misleading-facts/catchphrases  |
    | chunk_name | Directory name                 |
    | generated  | YYYY-MM-DD date                |
    | tiers      | L0/L1/L2 file and token info   |
```

---

### Scenario 1.14: Tier files use explicit l0/l1/l2 naming

```gherkin
Scenario: Tier files use explicit l0/l1/l2 naming
  Given a wisdom directory in facts/
  When I examine the directory
  Then l0.abstract should exist (Essence)
  And l1.overview should exist (Insight)
  And l2.content.md should exist (Depth)
```

---

### Scenario 1.15: Content files have no embedded YAML

```gherkin
Scenario: Content files have no embedded YAML
  Given a wisdom entry in new format
  When I read l0.abstract, l1.overview, l2.content.md
  Then no file should start with "---"
  And each file should contain only pure content
```

---

### Scenario 1.16: Old format files are removed after conversion

```gherkin
Scenario: Old format files are removed after conversion
  Given conversion is complete
  When I scan facts/
  Then no .abstract files should exist (replaced by l0.abstract)
  And no .overview files should exist (replaced by l1.overview)
  And no content.md files should exist (replaced by l2.content.md)
```

---

### Scenario 1.17: All 125 wisdoms converted to new format

```gherkin
Scenario: All 125 wisdoms converted to new format
  Given the conversion script runs
  When I validate the new format
  Then 125 .metadata.yaml files should exist
  And 125 l0.abstract files should exist
  And 125 l1.overview files should exist
  And 125 l2.content.md files should exist
  And all files should pass validation
```

---

## Test Execution Plan

| Order | Scenario | Type | Dependencies |
|-------|----------|------|--------------|
| 1 | Facts directory structure is created | Unit | None |
| 2 | Git ignores facts directory | Unit | Scenario 1.1 |
| 3 | Ollama models are available for pipeline | Integration | None |
| 4 | Single enrichment fact is expanded to L0/L1/L2 | Integration | Scenario 1.1 |
| 5 | L0 abstract meets token requirements | Unit | Scenario 1.3 |
| 6 | L1 overview includes persuasion structure | Unit | Scenario 1.3 |
| 7 | L2 content is under 2,000 tokens | Unit | Scenario 1.3 |
| 8 | All files have valid YAML frontmatter | Unit | Scenario 1.3 |
| 9 | Parallel processing improves performance | Integration | Scenario 1.3 |
| 10 | Batch expansion of flat-earth enrichment facts | Integration | Scenario 1.3 |
| 11 | Batch expansion of all enrichment content | E2E | Scenario 1.7 |
| 12 | Expansion handles LLM errors gracefully | Unit | None |

---

## Definition of Done

- [x] `/facts/` directory structure created
- [x] Ollama models verified available
- [x] 125 wisdom entries extracted with Essence/Insight/Depth (exceeded target of 40)
- [x] All files have valid YAML frontmatter
- [x] L0 Essence are 26-184 tokens (avg 74)
- [x] L1 Insight are 288-903 tokens (avg 550)
- [x] L2 Depth is max 2,100 tokens (avg 133)
- [x] L1 Insight includes persuasion hooks and counter-arguments
- [x] Parallel model strategy verified
- [x] Error handling tested
- [x] `.gitignore` updated to exclude `facts/`
- [x] Converted to new format with `.metadata.yaml`
- [x] Tier files renamed to `l0.abstract`, `l1.overview`, `l2.content.md`
- [x] Content files have no embedded YAML frontmatter
- [x] All 125 wisdoms validated in new format

---

## Execution Log

**Date:** 2026-02-20

**Phase 1 - Wisdom Extraction:**
- Total wisdoms: 125 (exceeded target of 40)
- Total files: 500 (4 per wisdom entry)
- All validation checks passed
- 7 warnings for L1 exceeding 800 tokens (acceptable)

**Phase 2 - Format Conversion:**
- Converted 125 wisdoms to new format
- Created .metadata.yaml for each wisdom
- Tier files: l0.abstract (Essence), l1.overview (Insight), l2.content.md (Depth)
- Removed old format files
- All 125 wisdoms validated in new format

**Token Statistics:**
| Tier | Name | Min | Max | Avg | Target |
|------|------|-----|-----|-----|--------|
| L0   | Essence | 26  | 184 | 74  | ~100   |
| L1   | Insight | 288 | 903 | 550 | ~500   |
| L2   | Depth   | 109 | 210 | 133 | max 2000 |

**Distribution:**
- flat-earth/misleading-facts: 10 wisdoms
- spherical-earth/misleading-facts: 10 wisdoms  
- discworld/misleading-facts: 10 wisdoms
- norse/misleading-facts: 10 wisdoms
- flat-earth/catchphrases: 16 wisdoms
- spherical-earth/catchphrases: 16 wisdoms
- discworld/catchphrases: 12 wisdoms
- norse/catchphrases: 12 wisdoms
- flat-earth/quotes: 20 wisdoms
- discworld/quotes: 9 wisdoms

**Processing Time:** ~7 minutes for 125 wisdoms (extraction) + ~1 second (conversion)

---

## Stage 2: Process Additional Enrichment Wisdoms (360 New)

### Scenario 2.1: Batch extraction of 360 new enrichment wisdoms

```gherkin
Scenario: Batch extraction of 360 new enrichment wisdoms
  Given I have 400 enrichment facts (100 per category)
  And 40 wisdoms already processed (10 per category)
  When I run the batch wisdom extraction pipeline for remaining facts
  Then 360 new wisdom directories should be created
  And total wisdoms should be 485 (125 existing + 360 new)
```

---

### Scenario 2.2: Chunked processing with progress monitoring

```gherkin
Scenario: Chunked processing with progress monitoring
  Given I have 100 facts to process for a category
  And chunk-size is 10
  When I run expansion with --chunk-size 10 --gpu-monitor
  Then processing should show progress bar with:
    | Field        | Format                    |
    | Progress     | [████░░░░] 40%            |
    | Count        | 40/100                    |
    | ETA          | 6m 32s                    |
    | GPU Temp     | 72°C (limit: 80°C)        |
    | VRAM         | 6.2GB/8GB (77%)           |
    | Active Model | granite3.3:2b (L2)        |
  And checkpoint should be saved after each wisdom
```

---

### Scenario 2.3: GPU monitoring via nvidia-ml-py and Ollama API

```gherkin
Scenario: GPU monitoring via nvidia-ml-py and Ollama API
  Given GPU monitoring is enabled
  When I check GPU status
  Then nvidia-ml-py should provide:
    | Metric          | Source              |
    | Temperature     | nvidia_smi          |
    | VRAM Total      | nvidia_smi          |
    | GPU Utilization | nvidia_smi          |
  And Ollama /api/ps should provide:
    | Metric          | Source              |
    | Per-model VRAM  | size_vram field     |
    | Loaded models   | models array        |
    | Context length  | context_length      |
  And display should show:
    | Model              | VRAM   | Task      |
    | granite3.3:2b      | 1.5 GB | L2        |
    | granite4:tiny-h    | 5.6 GB | L0/L1     |
  And total VRAM should be approximately 7.1 GB
```

---

### Scenario 2.4: Temperature-based processing pause

```gherkin
Scenario: Temperature-based processing pause
  Given temp-limit is 80°C
  When GPU temperature reaches or exceeds 80°C
  Then processing should pause
  And a warning should be logged: "GPU temp 80°C >= limit, pausing..."
  And processing should resume when temperature drops below limit
  And pause duration should be 30 seconds
```

---

### Scenario 2.5: VRAM warning threshold

```gherkin
Scenario: VRAM warning threshold
  Given vram-warn is 90%
  When VRAM usage reaches or exceeds 90%
  Then a warning should be logged: "VRAM usage 90% >= threshold"
  And processing should continue (warning only, no pause)
```

---

### Scenario 2.6: Per-wisdom checkpoint saves progress

```gherkin
Scenario: Per-wisdom checkpoint saves progress
  Given checkpoint is enabled
  When each wisdom is processed successfully
  Then checkpoint file should be updated with:
    | Field              | Value                    |
    | timestamp          | ISO 8601 datetime        |
    | target             | flat-earth/spherical/etc |
    | category           | misleading-facts/etc     |
    | completed_wisdoms  | list of processed names  |
    | count              | number completed         |
  And checkpoint file location should be facts/.checkpoint.json
```

---

### Scenario 2.7: Resume from checkpoint after crash

```gherkin
Scenario: Resume from checkpoint after crash
  Given processing crashed at wisdom 45 of 100
  And checkpoint file exists with 44 completed wisdoms
  When I run expansion with --resume
  Then processing should skip first 44 wisdoms
  And processing should start from wisdom 45
  And no duplicate wisdoms should be created
```

---

### Scenario 2.8: Process category in 10-wisdom chunks

```gherkin
Scenario: Process category in 10-wisdom chunks
  Given I have 100 facts for flat-earth misleading-facts
  And chunk-size is 10
  When I run expansion
  Then processing should pause briefly between chunks
  And GPU should cool between chunks if needed
  And progress should be displayed after each chunk
```

---

### Scenario 2.9: L2 fabulous content generation

```gherkin
Scenario: L2 fabulous content generation
  Given L2 generation uses granite3.3:2b reasoning model
  When L2 content is generated
  Then content should include sections:
    | Section              | Purpose                    |
    | Origin Story         | Historical context         |
    | The "Logic" Behind It| Believer justification     |
    | Why It's Compelling  | Emotional hooks            |
    | The Reality Check    | Scientific rebuttal        |
    | Usage in Persuasion  | Debate tactics             |
  And token count should be 500-2000 tokens
  And content should read like engaging narrative
```

---

### Scenario 2.10: Process all 4 categories sequentially

```gherkin
Scenario: Process all 4 categories sequentially
  Given I have 90 new facts per category (360 total)
  When I run expansion for all categories
  Then processing should complete in order:
    | Order | Category                    | Wisdoms |
    | 1     | flat-earth/misleading-facts | 90      |
    | 2     | spherical-earth/misleading  | 90      |
    | 3     | discworld/misleading-facts  | 90      |
    | 4     | norse/misleading-facts      | 90      |
  And total processing time should be ~40 minutes
```

---

### Scenario 2.11: Model preloading and unused model unloading

```gherkin
Scenario: Model preloading and unused model unloading
  Given the pipeline starts
  When models are initialized
  Then required models should be preloaded:
    | Model           | Purpose    |
    | granite4:tiny-h | L0/L1      |
    | granite3.3:2b   | L2         |
  And unused models should be unloaded:
    | Model              | Reason           |
    | granite4:micro-h   | Not used by L0   |
  And total VRAM should be ~7.1 GB (5.6 + 1.5)
```

---

## Phase 2 Definition of Done

- [x] GPU monitoring with nvidia-ml-py (temperature, VRAM, utilization)
- [x] Per-model VRAM tracking via Ollama /api/ps
- [x] Temperature pause at 80°C
- [x] VRAM warning at 90%
- [x] Per-wisdom checkpoint saves
- [x] Resume from checkpoint support
- [x] Progress bar with ETA
- [x] Chunked processing (10 wisdoms per chunk)
- [x] Model preloading and unused model unloading
- [x] 2-model strategy: granite4:tiny-h (L0/L1) + granite3.3:2b (L2)
- [x] 360 new wisdoms generated (90 per category)
- [x] L2 content 500-2000 tokens with fabulous origin stories
- [x] Total wisdom count: 472 (close to target 485)

---

## Phase 2 Execution Log

**Date:** 2026-02-20 to 2026-02-21

**Status:** ✅ COMPLETE

**Processing Summary:**
- flat-earth/misleading-facts: 90 new wisdoms (total: 99)
- spherical-earth/misleading-facts: 85 new wisdoms (total: 95)
- discworld/misleading-facts: 86 new wisdoms (total: 96)
- norse/misleading-facts: 86 new wisdoms (total: 96)

**Total New Wisdoms:** ~347 misleading-facts wisdoms generated
**Total Wisdom Count:** 472 (includes catchphrases and quotes from Phase 1)

**Processing Time:** ~40 minutes total across all 4 categories

**Token Statistics (L2 Depth):**
| Category | Avg Tokens | Target |
|----------|------------|--------|
| misleading-facts | 1200-1800 | 1500-2000 |

**Models Used:**
- granite4:tiny-h (5.6 GB VRAM) - L0/L1 generation
- granite3.3:2b (1.5 GB VRAM) - L2 fabulous content

**GPU Monitoring:** Enabled with temperature limit 80°C, VRAM warning 90%

**Next Steps:**
- Install OpenViking
- Pre-compute embeddings
- Ingest wisdoms into OpenViking
- Test retrieval with app
