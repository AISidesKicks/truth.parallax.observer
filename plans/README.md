> **For AI Coding Assistants**
>
> This `plans/` directory serves as the single source of truth for all implementation steps and architectural decisions.
>
> **Purpose:**
> - Keep overview of all implementation phases and progress
> - Enable quick familiarization for any new AI coding assistant joining the project
> - Document which parts are completed, in-progress, or just ideas to discuss with Human Coder
> - Allow experimentation with different tools and approaches while maintaining context
>
> **Guidelines for AI Assistants:**
> - Before starting ANY implementation, read relevant plan documents
> - Check `implementation-phases.md` for current progress status
> - Discuss with Human Coder before starting new phases or making architectural changes
> - After completing planed tasks, doubel check update of relevant plan documents
> - Keep plans synchronized with actual code changes
> - Use status markers: ✅ completed, 🔄 in-progress, 📋 planned, 💡 idea
> - Follow **BDD → TDD approach**: Read BDD scenarios in `bdd.md`, write failing tests first, then implement
>
> **Development Workflow:**
> 1. Read BDD feature/scenario from `bdd.md`
> 2. Write failing test (TDD red phase)
> 3. Implement minimal code to pass (TDD green phase)
> 4. Refactor if needed (TDD refactor phase)
> 5. Update plans and mark completed
>
> **Quality Note for AI Assistants:**
> - Human Coder is a non-native English speaker with dyslexia
> - Always double-check text in app and info files for grammar, spelling, and flow
> - Ensure smooth, natural English in all generated content
> - Fix typos and awkward phrasing proactively — don't assume it's intentional
>
> ---

# 🌍 parallax.observer

**Earthify you! Guaranteed!!!**

## What is this?

A µLAB for exploring GenAI persuasion and psychophancy for teens 16+. The AI agent (named after [Samuel Rowbotham](https://en.wikipedia.org/wiki/Samuel_Rowbotham)) will attempt to persuade you on the opposite opinion about Earth's shape:
- Flat Earth 🗺️
- Spherical Earth 🌐  
- Discworld (fictional) 🐢🐘🌍

## Features

- **Persuasive AI Agent** - Powered by Granite models via Ollama with CUDA acceleration
- **Vision Capabilities** - Qwen3-VL for image understanding, SigLIP for image search
- **Knowledge Database** - Curated sources with OpenViking agentic memory traversal
- **Interactive Web UI** - Terminal-style chat interface at localhost:8668
- **Session Memory** - Create an alterego, track conversations across sessions
- **Fun Facts** - "Why <this fact> is true. Period." style enrichment
- **Local Embeddings** - Infinity server with ModernBERT (text) + SigLIP (image)

## Content Philosophy

> **We are NOT an encyclopedic RAG.**

Quality over quantity. We don't need 100,000 facts for immersion.

**Targets:**
- **Testing:** ~300 targeted, funny, memorable facts
- **Production:** ~3,000-5,000 facts across all 4 persuasion targets

| What We Want | What We Don't Want |
|--------------|-------------------|
| Punchy catchphrases | Long encyclopedic articles |
| Memorable fun facts | Dry academic content |
| Humor with purpose | Boring data dumps |
| One concept per file | Overlapping information |

The goal is **persuasion playground**, not Wikipedia clone.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12 |
| LLM/VLM Runtime | Ollama (Docker) |
| Embeddings | Infinity (Docker) |
| Quantization | Q4_K_M (GGUF) |
| Optimization | Flash Attention, KV Cache 8-bit |
| Text Embeddings | ModernBERT via Infinity |
| Image Embeddings | SigLIP via Infinity |
| Memory | OpenViking |
| UI | Web-based terminal UI |
| Container | Docker + CUDA |
| Observability | OpenTelemetry + Phoenix |

### Models (Tested & Benchmarked)

See [plans/models.md](models.md) for full details.

**LLM/VLM (Ollama):**

| Model | Type | Size | Throughput | Use Case |
|-------|------|------|------------|----------|
| granite3.3:2b | Reasoning | 1.5 GB | 154.7 tok/s | Fast reasoning, thinking mode |
| granite4:tiny-h | MoE | 4.0 GB | 124.8 tok/s | Long context (128K), multilingual |
| granite4:micro-h | Hybrid | 2.0 GB | 107.6 tok/s | Lightweight, fast loading |
| qwen3-vl:2b | Vision | 1.9 GB | ~40 tok/s | Image analysis, OCR |

### Ollama Infrastructure

| Setting | Value |
|---------|-------|
| Host | `http://localhost:11433` |
| Flash Attention | Enabled |
| KV Cache | 8-bit (q8_0) |
| Context Length | 128K |

### Quick Start

```bash
# Start everything (default)
docker/up.sh

# Development mode
docker/up.sh dev

# Or run locally
./dev.sh
```

## Knowledge Sources

- [Discworld Geography](https://discworld.fandom.com/wiki/Discworld_geography)
- [Modern Flat Earth Beliefs](https://en.wikipedia.org/wiki/Modern_flat_Earth_beliefs)
- [LOC Flat Earth Guides](https://guides.loc.gov/flat-earth/books)

## Quick Start

```bash
# Development
./dev.sh          # Sets up conda environment

# Production  
docker/up.sh
```

App runs at **http://localhost:8668**

## Project Structure

```
├── plans/           # Technical planning documents
├── didactic/        # Educational methodology docs
├── www/             # Static pages (GitHub Pages)
├── docker/          # Unified Docker setup
│   ├── docker-compose.yml
│   ├── Dockerfile.app
│   ├── up.sh
│   ├── down.sh
│   ├── status.sh
│   └── tests.sh
└── src/             # Python backend
```

### Key Planning Documents

- [models.md](models.md) - LLM/VLM models (Ollama)
- [embeddings.md](embeddings.md) - Embedding model setup
- [docker.md](docker.md) - Docker architecture and containers
- [observability.md](observability.md) - Phoenix + OpenTelemetry setup
- [monitor.md](monitor.md) - GPU/CUDA monitoring and performance
- [gui.md](gui.md) - Terminal-style web interface and chat modes
- [agentic.md](agentic.md) - Multi-agent debate system and context management
- [memory.md](memory.md) - OpenViking memory system
- [dataset.md](dataset.md) - Knowledge sources
- [info-pages.md](info-pages.md) - xPAI parody content

## Language Support

Current: English [EN]  
Planned: Multi-language support

---

⚠️ **Disclaimer**: This is an educational/research µLAB. Some content is for FUN and may be subject to copyright (including unique translations). Not intended to actually convince anyone of any Earth shape theory.

*GenAI ALWAYS hallucinates. Or at least tries to persuade you. 😄*

## TODO / Roadmap

- [x] BDD testing: Model benchmarks completed
- [x] Select models based on benchmarks (Granite + Qwen3-VL)
- [ ] OpenViking runtime: Inter-agent communication
- [ ] User feature: Add new facts to knowledge base
- [ ] User feature: Personal memory (facts accepted/rejected)
- [ ] Multi-language support
- [ ] Mobile-responsive UI
