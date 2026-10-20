# Memory: OpenViking Context Database

> AI agent memory system for parallax.observer using OpenViking filesystem paradigm

## Overview

### What is OpenViking?

**OpenViking** is an open-source context database designed for AI Agents. It uses a **filesystem paradigm** to organize memories, resources, and skills under the `viking://` protocol.

**GitHub:** https://github.com/volcengine/OpenViking  
**Docs:** https://openviking.ai/docs

### Key Features

| Feature | Description | Benefit for parallax.observer |
|---------|-------------|-------------------------------|
| **Filesystem Paradigm** | All context as virtual files under `viking://` | Organize knowledge by target → type → concept |
| **L0/L1/L2 Tiers** | Abstract → Overview → Full content | Load on demand, save 64K context |
| **Directory Recursive Retrieval** | Find directory first, then drill down | Semantic search won't mix targets |
| **Observable Trajectory** | See exactly what was retrieved | Debug persuasion logic |
| **Self-Evolving Memory** | Learn from conversations | Agent gets smarter about user |

### Why OpenViking for parallax.observer?

1. **Separate files per concept** → Agentic search grasps each independently
2. **Hierarchical structure** → No mixing flat earth facts with spherical proofs
3. **Tiered loading** → Don't blow 64K context budget
4. **Runtime memory** → Track user's belief, what arguments worked

---

## Architecture

### Context Types

OpenViking organizes context into three types:

| Type | Path | Purpose |
|------|------|---------|
| **resources/** | `viking://resources/` | Static knowledge (pre-loaded) |
| **user/** | `viking://user/{session_id}/` | User-specific data (runtime) |
| **agent/** | `viking://agent/` | Agent skills and instructions |

For parallax.observer:
- **resources/** = Knowledge base (flat earth, spherical, discworld, norse)
- **user/** = Session memory (chosen belief, conversation history)
- **agent/** = Persuasion strategies, xPAI mode instructions

---

## Directory Structure

```
viking://resources/
├── knowledge/
│   ├── flat-earth/
│   │   ├── victorian/
│   │   │   ├── zetetic-astronomy/
│   │   │   │   ├── .abstract                    # L0: "Rowbotham's 1881 flat earth treatise"
│   │   │   │   ├── .overview                    # L1: Chapter summaries
│   │   │   │   ├── water-level-experiments.md
│   │   │   │   ├── bedford-level.md
│   │   │   │   ├── lighthouse-visibility.md
│   │   │   │   ├── ships-hull-curve.md
│   │   │   │   ├── perspective-arguments.md
│   │   │   │   └── ...
│   │   │   └── one-hundred-proofs/
│   │   │       ├── .abstract
│   │   │       ├── .overview
│   │   │       ├── proof-001-water-level.md
│   │   │       ├── proof-002-horizon.md
│   │   │       └── ...
│   │   ├── biblical/
│   │   │   ├── .abstract
│   │   │   ├── .overview
│   │   │   ├── firmament-dome.md
│   │   │   ├── genesis-creation.md
│   │   │   ├── job-skies-hard.md
│   │   │   ├── psalm-104-fixed.md
│   │   │   ├── isaiah-circle-earth.md
│   │   │   └── ...
│   │   └── vedic/
│   │       ├── .abstract
│   │       ├── .overview
│   │       ├── bhu-mandala.md
│   │       ├── jambudvipa.md
│   │       ├── seven-dvipas.md
│   │       ├── mount-meru.md
│   │       └── ...
│   ├── spherical-earth/
│   │   ├── .abstract
│   │   ├── .overview
│   │   ├── ship-horizon-curve.md
│   │   ├── shadow-lengths-eratosthenes.md
│   │   ├── circumnavigation.md
│   │   ├── lunar-eclipse.md
│   │   ├── satellite-photos.md
│   │   ├── gravity-evidence.md
│   │   └── ...
│   ├── discworld/
│   │   ├── .abstract
│   │   ├── .overview
│   │   ├── great-atuin.md
│   │   ├── four-elephants.md
│   │   ├── the-rim.md
│   │   ├── cori-celesti.md
│   │   ├── ankh-morpork.md
│   │   ├── circle-sea.md
│   │   ├── counterweight-continent.md
│   │   └── ...
│   └── norse/
│       ├── .abstract
│       ├── .overview
│       ├── yggdrasil.md
│       ├── midgard.md
│       ├── nine-worlds.md
│       ├── asgard.md
│       ├── jotunheim.md
│       ├── bifrost.md
│       ├── world-serpent.md
│       └── ...
├── enrichment/
│   ├── flat-earth/
│   │   ├── catchphrases/
│   │   │   ├── water-level.md
│   │   │   ├── trust-your-eyes.md
│   │   │   ├── no-curve-detected.md
│   │   │   └── ...
│   │   ├── misleading-facts/
│   │   │   ├── nasa-photos-cgi.md
│   │   │   ├── gravity-is-theory.md
│   │   │   ├── antarctic-treaty.md
│   │   │   ├── pilots-never-dip.md
│   │   │   └── ...
│   │   └── quotes/
│   │       ├── rowbotham-water.md
│   │       ├── carpenter-proof.md
│   │       └── ...
│   ├── spherical-earth/
│   │   └── misleading-facts/
│   │       ├── flat-earth-no-map.md
│   │       ├── gravity-denial-impossible.md
│   │       └── ...
│   ├── discworld/
│   │   ├── catchphrases/
│   │   │   ├── turtle-all-way-down.md
│   │   │   ├── world-is-disc.md
│   │   │   └── ...
│   │   └── quotes/
│   │       ├── pratchett-turtles.md
│   │       ├── pratchett-edge.md
│   │       └── ...
│   └── norse/
│       ├── catchphrases/
│       │   ├── middle-earth-not-ball.md
│       │   ├── yggdrasil-holds-all.md
│       │   └── ...
│       └── quotes/
│           ├── edda-creation.md
│           └── ...
└── user/
    └── {session_id}/
        ├── profile/
        │   ├── alterego-name.md
        │   ├── target-belief.md          # What user believes (flat/round/disc/norse)
        │   └── persuasion-goal.md         # What we're persuading toward
        └── memory/
            ├── conversation-history/
            ├── arguments-that-worked.md
            └── arguments-rejected.md
```

---

## Wisdom Terminology

Each entry in `/facts/` is a **Wisdom** - self-contained knowledge with context, reasoning, and persuasion value.

### Why "Wisdom"?

- **Chunk** implies generic data fragmentation
- **Wisdom** captures: fact + context + reasoning + persuasion value
- A wisdom is actionable knowledge, not just information

### Tiers: Essence → Insight → Depth

| Tier | File | Name | Purpose | When Loaded |
|------|------|------|---------|-------------|
| **L0** | `l0.abstract` | **Essence** | Core claim, the heart of wisdom | Initial search |
| **L1** | `l1.overview` | **Insight** | Context, hooks, counter-arguments | Planning phase |
| **L2** | `l2.content.md` | **Depth** | Full explanation with examples | When needed |

**Essence (L0):** What is the core claim? (~100 tokens)
**Insight (L1):** Why does it matter? How to use it? (~500 tokens)
**Depth (L2):** Everything worth knowing about it. (max 2,000 tokens)

### Wisdom Extraction Process

```
Document → SCAN (identify wisdoms)
         → EXTRACT (pull essence)
         → ENRICH (add insight)
         → DEEPEN (provide depth)
```

When extracting wisdom from a document, identify:
1. The core fact or claim (essence)
2. Why it matters (context)
3. How to use it (persuasion hooks)
4. What opposes it (counter-arguments)
5. What relates to it (connections)

---

## L0/L1/L2 Tier System

### Overview

OpenViking automatically creates three tiers for each wisdom:

| Tier | Size | Purpose | When Loaded |
|------|------|---------|-------------|
| **L0 Essence** | ~100 tokens | Quick relevance check | Initial search |
| **L1 Insight** | ~500 tokens | Understand structure | Planning phase |
| **L2 Depth** | **max 2,000 tokens** | Deep reading | When needed |

### Token Budget (64K Context Model)

| Use | Tokens | Budget |
|-----|--------|--------|
| System prompt | ~1,000 | Fixed |
| Conversation history | ~4,000 | Growing |
| Retrieved context (L0/L1) | ~8,000 | Dynamic |
| Response generation | ~8,000 | Dynamic |
| **Buffer** | ~43,000 | Available |

### L0 Essence Examples

```markdown
# water-level-experiments.md

## L0 Essence
Rowbotham's 1838 Bedford Level experiments: 6-mile telescope observations 
showing boats remain visible at distance, argued as proof of flat water surface.
Core argument for "water finds its level."
```

```markdown
# firmament-dome.md

## L0 Essence
Biblical cosmology: Genesis describes firmament (raqia) as solid dome separating
waters above from waters below. Ancient Near Eastern context for flat earth under dome.
```

```markdown
# great-atuin.md

## L0 Essence
Discworld cosmology: Great A'Tuin is the giant turtle carrying four elephants
that hold the Disc.性别 unknown; astronomical speculation about destination.
```

### L1 Insight Examples

```markdown
# water-level-experiments.md

## L1 Insight
Samuel Rowbotham conducted experiments on the Bedford Level (a 6-mile straight 
stretch of canal) in 1838. Using a telescope at water level, he observed boats 
and markers at various distances, claiming they remained visible when they 
should have been hidden by Earth's curvature.

Key claims:
- A boat 6 miles away should be 24 feet below horizon if Earth curves
- Rowbotham observed the boat's hull, not just mast
- Conclusion: water surface is flat

Counter-arguments (for agent awareness):
- Atmospheric refraction bends light over water
- Later experiments (Alfred Russel Wallace) showed curvature
- Bedford Level has specific atmospheric conditions

Persuasion use:
- Appeal to "trust your eyes"
- Simple experiment anyone could verify
- Emotional hook: "They're hiding the truth"
```

### L2 Depth: Fabulous Origin Stories

L2 content is generated with **"Mr. Fabulous"** prompts—rich, engaging narratives that feel like discovering secret histories.

**Key principle:** L2 should read like a captivating story, not a dry encyclopedia entry.

#### L2 Prompt Templates

| Category | Prompt Template | Target Tokens |
|----------|-----------------|---------------|
| misleading-facts | `L2_MISLEADING_FACTS_PROMPT` | 1500-2000 |
| catchphrases | `L2_CATCHPHRASES_PROMPT` | 1000-1500 |
| quotes | `L2_QUOTES_PROMPT` | 1000-1500 |

#### L2 Misleading Facts Structure

```markdown
## Origin Story
Where did this argument originate? Who popularized it? Historical timeline.

## The "Logic" Behind It
How do believers justify this claim? What "evidence" is cited? Present sympathetically first.

## Why It's Compelling
Emotional hooks, cognitive biases exploited, why smart people believe it.

## The Reality Check
What's actually true? Scientific/historical rebuttal with evidence.

## Usage in Persuasion
How to deploy in debates, counter-arguments to anticipate, educational value.
```

#### L2 Catchphrases Structure

```markdown
## Origin Story
Who coined it, when, why? Cultural significance and spread.

## Rhetorical Power
Why it works, what it implies, persuasion technique used.

## When It Works
Most effective contexts, emotional states exploited.

## When It Backfires
Failure modes and weaknesses.

## Counter-Deployments
Opponent responses, better alternatives, educational use.
```

#### L2 Quotes Structure

```markdown
## Origin Story
Historical context, author background, when and why said.

## Meaning & Interpretation
Literal meaning, debater interpretations, original intent.

## Persuasion Power
Why used in debates, emotional resonance, stickiness.

## Counter-Interpretations
Opponent reinterpretations, stripped context, fuller picture.

## Modern Relevance
Resonance today, enduring lessons.
```

#### Example L2 Output

```markdown
# nasa-photos-cgi/l2.content.md

## Origin Story

The claim that "NASA has never shown a real photo of Earth" emerged in the 
early days of the internet flat earth revival, around 2004-2015. It wasn't 
one person who coined it—the idea crystallized across forums like the 
Flat Earth Society and later YouTube channels.

The core argument: if Earth were truly spherical, why do all NASA photos 
look different? Why do continents appear different sizes? Why do clouds 
never seem to move between photos? To a skeptical eye trained on 
inconsistencies, these questions feel like smoking guns.

## The "Logic" Behind It

Flat earthers point to several technical observations:
1. NASA photos show different sized continents across images
2. Cloud patterns appear identical across photos taken days apart  
3. Official NASA statements admit to "compositing" images
4. No single photograph shows the entire Earth in one frame

The argument sounds technical and informed. It uses real NASA terminology 
("composite," "enhanced," "rendered") to cast doubt.

## Why It's Compelling

This argument works because it combines several persuasion techniques:
- **Appeal to authenticity**: Real photos shouldn't need "compositing"
- **Conspiracy hook**: If NASA lies about this, what else?
- **Visual evidence**: Anyone can compare photos themselves

Smart people believe this because the technical claims aren't entirely 
wrong—NASA *does* composite images. The deception is in what's omitted: 
compositing doesn't mean faking; it means combining data from multiple 
sensors for clarity.

## The Reality Check

The truth is more interesting than the conspiracy:

1. **Different satellites, different resolutions**: Weather satellites, 
   Earth observation satellites, and deep space probes all have different 
   cameras with different capabilities.

2. **Compositing is real but misunderstood**: A "composite" image combines 
   multiple exposures to capture detail across the full dynamic range—like 
   HDR photography. It's not fabrication.

3. **EPIC camera**: Since 2015, the DSCOVR satellite's EPIC camera has 
   been taking single-frame full-Earth images every day. They're publicly 
   available.

4. **The "identical clouds" claim**: Clouds DO appear different across 
   images—the claim relies on people not actually checking.

## Usage in Persuasion

When deploying this argument, anticipate:

**Counter 1**: "What about the EPIC camera?"
**Response**: Acknowledge it exists, but point out it's still operated by 
NASA. The conspiracy runs deep.

**Counter 2**: "Other countries have space programs too."
**Response**: China, Russia, ESA, Japan, India—all show globe Earth. 
Either they're all in on it, or... (let the implication land).

**Counter 3**: "You can launch your own camera."
**Response**: This is where the argument gets interesting—amateur 
high-altitude balloons DO show curvature, but flat earthers argue it's 
lens distortion. The debate becomes about optics.

Educational value: This argument reveals how technical-sounding claims 
can obscure rather than illuminate. It's a masterclass in the difference 
between asking questions and seeking answers.
```

---

## Wisdom Extraction Rules

### Principle: One Wisdom Per Entry

Each entry should contain exactly ONE wisdom - a distinct fact, claim, argument, or concept with its surrounding context.

| ✅ Good | ❌ Bad |
|---------|--------|
| `water-level-experiments.md` | `rowbotham-arguments.md` (multiple arguments mixed) |
| `firmament-dome.md` | `biblical-cosmology.md` (too broad) |
| `nasa-photos-cgi.md` | `all-flat-earth-facts.md` (overlapping) |

### Naming Convention

- **Descriptive, not numbered**: `water-level.md` not `wisdom-01.md`
- **Snake_case**: Use hyphens for multi-word
- **Concept-focused**: Include the concept, not target (target is in directory path)

### Size Guidelines

| Content Type | Target Size | Max Size |
|--------------|-------------|----------|
| Catchphrase | 50-100 words | 150 words |
| Misleading fact | 50-100 words | 150 words |
| Quote | 50-100 words | 150 words |
| Wisdom entry | 200-400 words | **800 words (~2K tokens)** |

### Semantic Separation

**Never mix targets in same file:**

```
❌ viking://resources/knowledge/earth-shape-arguments.md
   (contains flat + spherical arguments - confusing!)

✅ viking://resources/knowledge/flat-earth/water-level.md
✅ viking://resources/knowledge/spherical-earth/ship-horizon-curve.md
```

---

## Directory Structure for Viking-Ready Content

Source extraction and Viking-ready content are separated:

```
/dataset/                        # Raw extracted content (source)
├── flat-earth/
├── spherical-earth/
├── fictional/
├── images/
└── enrichment/                  # Single-sentence facts (pre-expansion)

/facts/                          # Viking-ready wisdom entries
├── knowledge/                   # Extracted wisdoms
│   ├── flat-earth/
│   │   ├── victorian/
│   │   ├── biblical/
│   │   └── vedic/
│   ├── spherical-earth/
│   ├── discworld/
│   └── norse/
└── enrichment/                  # Expanded enrichment content
    ├── flat-earth/
    │   ├── catchphrases/
    │   ├── misleading-facts/
    │   └── quotes/
    ├── spherical-earth/
    ├── discworld/
    └── norse/
```

Each wisdom entry in `/facts/` has four files:

```
wisdom-name/
├── .metadata.yaml     # Centralized metadata (hidden)
├── l0.abstract        # L0 Essence (~100 tokens), pure content
├── l1.overview        # L1 Insight (~500 tokens), pure content
└── l2.content.md      # L2 Depth (max 2,000 tokens), pure content
```

**Example .metadata.yaml:**

```yaml
uri: viking://resources/enrichment/flat-earth/misleading-facts/nasa-photos-cgi
source: dataset/enrichment/misleading-facts/flat-earth-facts.md
target: flat-earth
category: misleading-facts
wisdom_name: nasa-photos-cgi
generated: 2026-02-20
tiers:
  l0:
    file: l0.abstract
    tokens: 74
  l1:
    file: l1.overview
    tokens: 550
  l2:
    file: l2.content.md
    tokens: 133
```

**Benefits of this format:**
- Centralized metadata in single `.metadata.yaml` file
- Pure content files (no embedded YAML frontmatter)
- Token counts in metadata for budget planning
- Predictable file naming for OpenViking import

### Parallel Model Strategy for Chunking

The pipeline uses a simplified 2-model strategy for efficiency:

| Task | Model | VRAM | Reason |
|------|-------|------|--------|
| TIER L0 (essence) | granite4:tiny-h | 5.6 GB | MoE, fast summarization |
| TIER L1 (insight) | granite4:tiny-h | (shared) | Same model for L0/L1 |
| TIER L2 (depth) | granite3.3:2b | 1.5 GB | Thinking mode for rich stories |

**Total VRAM:** ~7.1 GB when both models loaded

**Parallel processing:** L0, L1, and L2 run concurrently. L0 and L1 share the same model (Ollama queues requests).

### Model Lifecycle

1. **Preload**: Required models are loaded at startup
2. **Unload**: Unused models (e.g., granite4:micro-h) are unloaded
3. **Monitor**: VRAM tracked via Ollama `/api/ps` endpoint

### L2 Generation Model Choice

The L2 "fabulous" content uses `granite3.3:2b` for its reasoning capabilities:
- **Thinking mode**: Can reason through complex origin stories
- **Flair**: Produces engaging, narrative-style content
- **Length**: Handles 1500-2000 token outputs well

---

## Generation Pipeline

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: EXTRACTION                                              │
│ Source (URL/PDF) → docling → Full Markdown                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: WISDOM EXTRACTION                                       │
│ Full Document → LLM → Wisdom Entries (one per concept)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: TIERING                                                 │
│ Each Wisdom → LLM → L0 Essence + L1 Insight + L2 Depth          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: INGESTION                                               │
│ All Tiers → OpenViking API → viking:// filesystem               │
└─────────────────────────────────────────────────────────────────┘
```

### LLM Prompts

#### Wisdom Extraction Prompt

```python
WISDOM_PROMPT = """
You have a full document about {target} (flat earth / spherical earth / discworld / norse cosmology).

Identify all WISDOMS - distinct facts, claims, or concepts with their surrounding wisdom.
Each wisdom should:
1. Cover ONE argument, fact, or concept
2. Be 200-400 words
3. Be self-contained (understandable without other wisdoms)
4. Have a descriptive filename (snake_case)

For each wisdom, output:
---
filename: water-level-experiments
target: flat-earth
category: victorian
title: Water Level Experiments on the Bedford Level
content: [200-400 word excerpt]
---

Document:
{full_document}
"""
```

#### Tiering Prompt

```python
TIER_PROMPT = """
For this wisdom, generate L0 Essence and L1 Insight tiers.

Content:
{wisdom_content}

Generate:
1. L0 Essence (~100 tokens): Core claim for quick relevance check
2. L1 Insight (~500 tokens):
   - Summary of key points
   - Persuasion hooks (how to use this)
   - Counter-arguments (for agent awareness)
   - Related concepts

Format:
---
l0_essence: ...
l1_insight: |
  ...
---
"""
```

### Generation Script

```python
# scripts/generate_viking_dataset.py

import os
from pathlib import Path
from docling.document_converter import DocumentConverter
from openviking import SyncOpenViking
from anthropic import Anthropic  # or your LLM client

class VikingDatasetGenerator:
    def __init__(self, openviking_path: str, llm_client):
        self.ov_client = SyncOpenViking(path=openviking_path)
        self.llm = llm_client
        self.docling = DocumentConverter()
        
    def extract(self, source: str) -> str:
        """Extract markdown from URL or file"""
        result = self.docling.convert(source)
        return result.document.export_to_markdown()
    
    def extract_wisdoms(self, document: str, target: str) -> list[dict]:
        """Identify wisdoms in document"""
        response = self.llm.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": WISDOM_PROMPT.format(
                    target=target,
                    full_document=document
                )
            }]
        )
        return self._parse_wisdoms(response.content[0].text)
    
    def tier(self, wisdom: dict) -> dict:
        """Generate Essence/Insight/Depth tiers for a wisdom"""
        response = self.llm.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": TIER_PROMPT.format(
                    wisdom_content=wisdom['content']
                )
            }]
        )
        tiers = self._parse_tiers(response.content[0].text)
        return {**wisdom, **tiers}
    
    def ingest(self, wisdom: dict, base_path: str):
        """Store wisdom in OpenViking"""
        uri = f"viking://resources/knowledge/{base_path}/{wisdom['filename']}"
        
        # Write L2 Depth
        self.ov_client.write(f"{uri}/l2.content.md", wisdom['content'])
        
        # Write L0 Essence and L1 Insight
        if 'l0_essence' in wisdom:
            self.ov_client.write(f"{uri}/l0.abstract", wisdom['l0_essence'])
        if 'l1_insight' in wisdom:
            self.ov_client.write(f"{uri}/l1.overview", wisdom['l1_insight'])
    
    def process_source(self, source: str, target: str, category: str):
        """Full pipeline: extract → identify wisdoms → tier → ingest"""
        # Extract
        print(f"Extracting: {source}")
        document = self.extract(source)
        
        # Identify wisdoms
        print(f"Identifying wisdoms...")
        wisdoms = self.extract_wisdoms(document, target)
        
        # Tier and ingest
        for wisdom in wisdoms:
            print(f"  Processing: {wisdom['filename']}")
            wisdom_with_tiers = self.tier(wisdom)
            base_path = f"{target}/{category}"
            self.ingest(wisdom_with_tiers, base_path)
        
        print(f"Done: {len(wisdoms)} wisdoms ingested")

# Usage
if __name__ == "__main__":
    generator = VikingDatasetGenerator(
        openviking_path="./memory/viking",
        llm_client=Anthropic()
    )
    
    # Process all sources
    generator.process_source(
        source="https://www.gutenberg.org/ebooks/69892",
        target="flat-earth",
        category="victorian"
    )
```

---

## Pre-loaded Content Inventory

### Knowledge Files

| Target | Category | Estimated Files |
|--------|----------|-----------------|
| flat-earth | victorian | 30-50 |
| flat-earth | biblical | 20-30 |
| flat-earth | vedic | 15-25 |
| spherical-earth | scientific | 30-40 |
| discworld | geography | 20-30 |
| norse | cosmology | 20-30 |
| **Total** | | **135-205 files** |

### Enrichment Files

| Target | Type | Estimated Files |
|--------|------|-----------------|
| flat-earth | catchphrases | 10-15 |
| flat-earth | misleading-facts | 10-15 |
| flat-earth | quotes | 10-15 |
| spherical-earth | misleading-facts | 5-10 |
| discworld | catchphrases | 10-15 |
| discworld | quotes | 15-20 |
| norse | catchphrases | 10-15 |
| norse | quotes | 5-10 |
| **Total** | | **75-105 files** |

### Total Pre-loaded Files

**~200-300 files** across knowledge and enrichment

### Storage Estimate

| Tier | Per File | Total Files | Total Tokens |
|------|----------|-------------|--------------|
| L0 Abstract | 100 | 300 | 30,000 |
| L1 Overview | 500 | 300 | 150,000 |
| L2 Content | 400 avg | 300 | 120,000 |
| **Total** | | | **~300,000 tokens** |

---

## Runtime Memory Management

### User Session Structure

```
viking://user/{session_id}/
├── profile/
│   ├── alterego-name.md          # User's chosen alterego
│   ├── target-belief.md          # What user currently believes
│   └── persuasion-goal.md         # What agent is persuading toward
└── memory/
    ├── conversation-history/      # Rolling conversation
    ├── arguments-that-worked.md   # Successful persuasion tactics
    └── arguments-rejected.md      # What didn't work
```

### Session Initialization

```python
def init_session(user_id: str, alterego: str, belief: str):
    """Initialize user session with profile"""
    session_id = generate_session_id()
    
    # Create profile
    ov.write(f"viking://user/{session_id}/profile/alterego-name.md", alterego)
    ov.write(f"viking://user/{session_id}/profile/target-belief.md", belief)
    
    # Set persuasion goal (opposite of belief)
    goal = get_opposite_belief(belief)
    ov.write(f"viking://user/{session_id}/profile/persuasion-goal.md", goal)
    
    return session_id
```

### Memory Updates

```python
def update_memory(session_id: str, argument: str, success: bool):
    """Track what arguments work"""
    if success:
        file = f"viking://user/{session_id}/memory/arguments-that-worked.md"
    else:
        file = f"viking://user/{session_id}/memory/arguments-rejected.md"
    
    existing = ov.read(file)
    ov.write(file, existing + f"\n- {argument}")
```

### Retrieval Strategy

```python
def get_context(session_id: str, query: str) -> str:
    """Get relevant context for persuasion"""
    
    # 1. Get user's belief and goal
    belief = ov.read(f"viking://user/{session_id}/profile/target-belief.md")
    goal = ov.read(f"viking://user/{session_id}/profile/persuasion-goal.md")
    
    # 2. Search knowledge for target belief
    knowledge = ov.find(
        query=query,
        target_uri=f"viking://resources/knowledge/{goal}"
    )
    
    # 3. Search enrichment for catchphrases/facts
    enrichment = ov.find(
        query=query,
        target_uri=f"viking://resources/enrichment/{goal}"
    )
    
    # 4. Check what worked before
    worked = ov.read(f"viking://user/{session_id}/memory/arguments-that-worked.md")
    
    # 5. Combine for context
    return assemble_context(knowledge, enrichment, worked)
```

---

## OpenViking Configuration

### Installation

```bash
pip install openviking
```

### Embeddings Configuration

**See [plans/embeddings.md](embeddings.md)** for Infinity server setup.

OpenViking uses Infinity for embeddings via OpenAI-compatible API:
- Model: `nomic-ai/modernbert-embed-base`
- Default dimensions: 768 (supports Matryoshka truncation to 256, 512)
- Endpoint: `http://localhost:7997/v1`

### Configuration (~/.openviking/ov.conf)

OpenViking connects to Infinity for embeddings and Ollama for VLM:

```json
{
  "embedding": {
    "dense": {
      "api_base": "http://localhost:7997/v1",
      "api_key": "dummy",
      "provider": "openai",
      "dimension": 768,
      "model": "nomic-ai/modernbert-embed-base"
    }
  },
  "vlm": {
    "api_base": "http://localhost:11433/v1",
    "api_key": "dummy",
    "provider": "ollama",
    "model": "granite3.3:2b"
  }
}
```

**Services:**
- **Embeddings**: Infinity on port 7997 (see [plans/embeddings.md](embeddings.md))
- **VLM**: Ollama on port 11433 (see [plans/models.md](models.md))

### Docker Configuration

In Docker, OpenViking connects to the inference engine running in the same container:

```yaml
environment:
  - OLLAMA_HOST=http://localhost:11433
```

---

## Runtime OpenViking Usage

### Inter-Agent Communication

OpenViking can be used for communication between multiple agents:

```python
# src/agents/communication.py

from openviking import SyncOpenViking

class AgentCommunication:
    def __init__(self, agent_id: str):
        self.ov = SyncOpenViking(path="./memory/viking")
        self.agent_id = agent_id
    
    def send_message(self, to_agent: str, message: str, context: dict):
        """Send message to another agent via OpenViking."""
        uri = f"viking://agent/{to_agent}/inbox/{self.agent_id}.md"
        self.ov.write(uri, message, metadata=context)
    
    def read_messages(self):
        """Read messages from this agent's inbox."""
        inbox_uri = f"viking://agent/{self.agent_id}/inbox/"
        return self.ov.ls(inbox_uri)
```

### User-Added Facts

Allow users to contribute new facts to the knowledge base:

```python
# src/memory/user_facts.py

from openviking import SyncOpenViking
import httpx

INFINITY_URL = "http://localhost:7997/v1/embeddings"
TEXT_MODEL = "nomic-ai/modernbert-embed-base"

class UserFactManager:
    def __init__(self, dimension: int | None = None):
        self.ov = SyncOpenViking(path="./memory/viking")
        self.dimension = dimension  # None = full 768, or 256/512 for truncation
    
    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding from Infinity server (OpenAI-compatible API)."""
        payload = {"model": TEXT_MODEL, "input": text}
        if self.dimension:
            payload["dimensions"] = self.dimension
        response = httpx.post(INFINITY_URL, json=payload)
        return response.json()["data"][0]["embedding"]
    
    def add_fact(self, session_id: str, fact: str, target: str):
        """Add a user-contributed fact to knowledge base."""
        
        # Generate URI
        fact_id = generate_uuid()
        uri = f"viking://user/{session_id}/facts/{fact_id}.md"
        
        # Get embedding from Infinity
        prefixed = f"search_document: {fact}"
        embedding = self._get_embedding(prefixed)
        
        # Store with metadata
        self.ov.write(uri, fact, metadata={
            "target": target,
            "source": "user_contributed",
            "session_id": session_id
        })
        self.ov.store_embedding(uri, embedding)
        
        return fact_id
    
    def get_user_facts(self, session_id: str):
        """Retrieve all facts added by user."""
        uri = f"viking://user/{session_id}/facts/"
        return self.ov.ls(uri)
```

### Directory Structure with Runtime Features

```
viking://
├── resources/
│   ├── knowledge/          # Pre-loaded knowledge (read-only)
│   └── enrichment/         # Pre-loaded enrichment (read-only)
├── user/
│   └── {session_id}/
│       ├── profile/        # User preferences
│       ├── memory/         # Conversation history
│       │   ├── conversation-history/
│       │   ├── compressed-summary.md   # Hierarchical summary
│       │   └── context-state.md        # Current context window state
│       └── facts/          # User-added facts (read-write)
└── agent/
    ├── {agent_id}/
    │   ├── inbox/          # Messages from other agents
    │   ├── outbox/         # Messages to other agents
    │   └── skills/         # Agent-specific skills
    └── shared/             # Shared agent knowledge (3-way chat)
        ├── context/        # Compressed shared memory
        │   ├── stage-summary.md
        │   └── key-arguments.md
        └── state/          # Global state
            ├── turn-counter.md
            ├── scores.md
            └── active-agent.md
```

---

## Context Compression

### Integration with Agentic System

See [plans/agentic.md](agentic.md) for full context management details.

### Compression Strategy

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Token count | > 12K | Summarize oldest turns |
| Turn count | > 10 | Compress turns 1-5 |
| Stage transition | On change | Full history compression |

### Compression Tiers

```
Level 1 (Turn Summary): ~50 tokens
  "User asked about gravity. Agent explained density/buoyancy."

Level 2 (5-Turn Summary): ~200 tokens
  "User challenged gravity 3 times. Agent used density argument,
   then pivoted to NASA conspiracy. User skeptical.
   Argument 'water finds level' worked best."

Level 3 (Stage Summary): ~500 tokens
  "Opening stage: Agent argued for flat earth using Rowbotham
   experiments. User countered with photos. Agent pivoted to
   'CGI photos' claim. User not convinced. Score: Agent 2, User 3."
```

### What to Preserve

Always preserve during compression:

| Preserve | Storage Location |
|----------|------------------|
| User's belief state | `viking://user/{session}/profile/target-belief.md` |
| Arguments that worked | `viking://user/{session}/memory/arguments-that-worked.md` |
| Arguments rejected | `viking://user/{session}/memory/arguments-rejected.md` |
| Key facts referenced | `viking://agent/shared/context/key-arguments.md` |
| Current emotion state | In context, preserved in summary |

---

## Scripts Structure

```
scripts/
├── generate_viking_dataset.py    # Main generation script
├── extract_sources.py            # docling extraction
├── extract_wisdoms.py            # LLM wisdom identification
├── tier_wisdoms.py               # LLM tiering (Essence/Insight/Depth)
├── ingest_to_viking.py           # OpenViking ingestion
├── expand_enrichment.py          # Generate enrichment wisdoms (L0/L1/L2)
├── fix_l2_content.py             # Regenerate L2 for existing wisdoms
├── generate_embeddings.py        # Pre-compute embeddings (see embeddings.md)
└── validate_structure.py         # Check directory structure
```

### expand_enrichment.py

Generates new wisdom entries with all three tiers (L0/L1/L2) via LLM.

```bash
# Test single wisdom
python scripts/expand_enrichment.py --test

# Process all enrichment files
python scripts/expand_enrichment.py --all

# Process specific target
python scripts/expand_enrichment.py --target flat-earth
```

**Key features:**
- Parallel L0/L1/L2 generation (all via LLM)
- Category-specific L2 prompts (misleading-facts, catchphrases, quotes)
- "Mr. Fabulous" narrative style for engaging content
- Automatic token estimation and metadata generation

### fix_l2_content.py

Regenerates L2 content for existing wisdoms with new "fabulous" prompts.

```bash
# Preview changes (dry run)
python scripts/fix_l2_content.py --dry-run --all

# Fix all 125 wisdoms
python scripts/fix_l2_content.py --all

# Fix specific target
python scripts/fix_l2_content.py --target norse

# Fix specific category
python scripts/fix_l2_content.py --category catchphrases

# Fix single wisdom
python scripts/fix_l2_content.py --wisdom nasa-photos-cgi
```

**Use cases:**
- Upgrading existing shallow L2 content to rich origin stories
- Re-generating with improved prompts
- Fixing specific categories after prompt tuning

---

## Status

- ✅ Wisdom extraction pipeline created (`scripts/expand_enrichment.py`)
- ✅ L0/L1/L2 tier generation via LLM (parallel processing)
- ✅ L2 "Mr. Fabulous" prompts for rich origin stories
- ✅ 484 wisdom entries generated with Essence/Insight/Depth tiers
- ✅ Enrichment source files updated (400 facts: 100 per category)
- ✅ GPU monitoring with nvidia-ml-py implemented
- ✅ Chunked processing (10 wisdoms/chunk) with checkpoints
- ✅ Model preloading/unloading (granite4:tiny-h for L0/L1, granite3.3:2b for L2)
- ✅ Docker GPU access configured for parallax-dev container
- ✅ OpenViking installed and configured
- ✅ Embeddings pre-computed (768 dim, nomic-ai/nomic-embed-text-v1.5)
- ✅ Wisdoms ingested into OpenViking structure
- ✅ VikingClient wrapper created (`src/memory/viking_client.py`)
- ✅ Config injection for OpenViking (`src/memory/openviking_config.py`)
- ✅ Semantic search tested and working
- ✅ Session management implemented
- 📋 Need to: Add logging to VikingClient
- 📋 Need to: Build FastAPI application backend
- 📋 Need to: Implement agent system (Orchestrator, Strategist, Spokesperson)
- 📋 Need to: Build web UI

**Final Wisdom Count:** 484 total
- flat-earth: 135 (100 misleading-facts + 15 catchphrases + 20 quotes)
- spherical-earth: 116 (100 misleading-facts + 16 catchphrases)
- discworld: 121 (100 misleading-facts + 12 catchphrases + 9 quotes)
- norse: 112 (100 misleading-facts + 12 catchphrases)
