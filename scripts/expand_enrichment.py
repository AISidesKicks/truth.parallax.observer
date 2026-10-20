#!/usr/bin/env python3
"""
Wisdom Extraction Pipeline - Extract wisdoms with Essence/Insight/Depth tiers.

Each wisdom entry contains:
- L0 Essence (l0.abstract): Core claim (~100 tokens)
- L1 Insight (l1.overview): Context, hooks, counter-arguments (~500 tokens)
- L2 Depth (l2.content.md): Full explanation (max 2K tokens)

Usage:
    python scripts/expand_enrichment.py --test                    # Test with one wisdom
    python scripts/expand_enrichment.py --target flat-earth       # Process target
    python scripts/expand_enrichment.py --all                     # Process all
    python scripts/expand_enrichment.py --target flat-earth --category misleading-facts --chunk-size 10 --gpu-monitor
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

try:
    import nvidia_smi
    NVIDIA_SMI_AVAILABLE = True
except ImportError:
    nvidia_smi = None
    NVIDIA_SMI_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11433/api/generate"
OLLAMA_PS_URL = "http://localhost:11433/api/ps"
OLLAMA_UNLOAD_URL = "http://localhost:11433/api/generate"
CHECKPOINT_FILE = Path("facts/.checkpoint.json")

MODELS = {
    "extract": "granite3.3:2b",
    "tier_l0": "granite4:tiny-h",    # MoE model for L0/L1
    "tier_l1": "granite4:tiny-h",    # Same model for L0/L1
    "tier_l2": "granite3.3:2b",      # Thinking model for rich L2 content
}

MODEL_INFO = {
    "granite3.3:2b": {"size_gb": 1.5, "type": "Thinking", "task": "L2"},
    "granite4:tiny-h": {"size_gb": 5.6, "type": "MoE", "task": "L0/L1"},
}

ENRICHMENT_DIR = Path("dataset/enrichment")
FACTS_DIR = Path("facts/enrichment")

TIER_L0_PROMPT = """Generate a concise L0 abstract (~100 tokens) for this content.

Content:
{content}

Requirements:
- 50-150 tokens
- Summarize the core claim
- Include key argument
- Brief counter-point if relevant
- Output ONLY the abstract text, no markdown headers

Abstract:"""

TIER_L1_PROMPT = """Generate an L1 overview (~500 tokens) for this content.

Content:
{content}

Requirements:
- 400-600 tokens
- Include these sections (use markdown headers):

## Summary
- Key points (3-5 bullet points)

## Persuasion Hooks
- How to use this in a debate
- Emotional angles that work

## Counter-Arguments
- For agent awareness
- What opponents might say

## Related Concepts
- Connected ideas (2-3)

Output the overview now:"""


# L2 "Fabulous" Prompts - Rich origin stories with depth

L2_MISLEADING_FACTS_PROMPT = """Generate a "fabulous origin story" for this misleading claim (~1500-2000 tokens).

Claim: {content}
Target: {target}

Create an engaging, educational expansion with these sections:

## Origin Story
Where did this argument originate? Who popularized it? What's the historical timeline? Make it feel like discovering a secret history.

## The "Logic" Behind It
How do believers justify this claim? What "evidence" do they cite? What makes it sound convincing on the surface? Present the argument sympathetically first.

## Why It's Compelling
What emotional hooks make this persuasive? What cognitive biases does it exploit? Why do smart people sometimes believe it?

## The Reality Check
What's actually true? Provide scientific/historical rebuttal with evidence. Be thorough but fair.

## Usage in Persuasion
How would you deploy this in a debate? What counter-arguments should you anticipate? What's the educational value?

Write with flair—make it memorable, witty, and genuinely educational. Think of yourself as Mr. Fabulous, the master storyteller of cosmological controversies.

Output ONLY the content, no meta-commentary."""


L2_CATCHPHRASES_PROMPT = """Generate a fabulous expansion of this catchphrase (~1000-1500 tokens).

Catchphrase: {content}
Target: {target}

Create an engaging expansion with these sections:

## Origin Story
Who coined this phrase? When and why? How did it spread? What cultural significance does it hold?

## Rhetorical Power
Why does this catchphrase work? What does it imply beyond the literal words? What persuasion technique does it use?

## When It Works
In what contexts is this catchphrase most effective? What emotional state does it exploit?

## When It Backfires
When might this catchphrase fail or be counter-productive? What are its weaknesses?

## Counter-Deployments
How do opponents respond? What are better alternatives? How can an agent use this educationally?

Write with wit and style—think of yourself as Mr. Fabulous, the raconteur of rhetorical delights.

Output ONLY the content, no meta-commentary."""


L2_QUOTES_PROMPT = """Generate a fabulous expansion of this quote (~1000-1500 tokens).

Quote: {content}
Target: {target}

Create an engaging expansion with these sections:

## Origin Story
What's the historical context of this quote? Who said/wrote it? When and why? What was happening in the world?

## Meaning & Interpretation
What does it literally mean? How do flat-earthers/cosmology-debaters interpret it? What was the original intended meaning?

## Persuasion Power
Why is this quote used in debates? What emotional resonance does it have? What makes it sticky in memory?

## Counter-Interpretations
How might opponents reinterpret this? What context is often stripped away? What's the fuller picture?

## Modern Relevance
How does this quote resonate today? What can we learn from its enduring power?

Write with scholarly flair and storytelling magic—be Mr. Fabulous, the historian of great quotations.

Output ONLY the content, no meta-commentary."""


# GPU Monitoring Classes

@dataclass
class ModelMemory:
    """Per-model memory info from Ollama API."""
    name: str
    size_vram_bytes: int
    context_length: int
    parameter_size: str
    
    @property
    def size_vram_gb(self) -> float:
        return self.size_vram_bytes / 1024**3


@dataclass
class GPUStatus:
    """GPU status from nvidia-ml-py."""
    temp_c: int
    vram_used_gb: float
    vram_total_gb: float
    vram_percent: float
    gpu_util: int
    should_pause: bool
    should_warn: bool


class GPUMonitor:
    """Monitor GPU using nvidia-ml-py and Ollama API."""
    
    def __init__(self, temp_limit: int = 80, vram_warn_percent: int = 90):
        self.temp_limit = temp_limit
        self.vram_warn_percent = vram_warn_percent
        self._initialized = False
        self._handle = None
        
        if NVIDIA_SMI_AVAILABLE and nvidia_smi is not None:
            try:
                nvidia_smi.nvmlInit()
                self._handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
                self._initialized = True
                logger.info("GPU monitoring initialized via nvidia-ml-py")
            except Exception as e:
                logger.warning(f"Failed to initialize nvidia-ml-py: {e}")
    
    def get_gpu_status(self) -> GPUStatus | None:
        """Get GPU metrics from nvidia-ml-py."""
        if not self._initialized or nvidia_smi is None or self._handle is None:
            return None
        
        try:
            mem = nvidia_smi.nvmlDeviceGetMemoryInfo(self._handle)
            util = nvidia_smi.nvmlDeviceGetUtilizationRates(self._handle)
            temp = nvidia_smi.nvmlDeviceGetTemperature(
                self._handle, nvidia_smi.NVML_TEMPERATURE_GPU
            )
            
            vram_percent = (mem.used / mem.total) * 100
            
            return GPUStatus(
                temp_c=temp,
                vram_used_gb=mem.used / 1024**3,
                vram_total_gb=mem.total / 1024**3,
                vram_percent=vram_percent,
                gpu_util=util.gpu,
                should_pause=temp >= self.temp_limit,
                should_warn=vram_percent >= self.vram_warn_percent,
            )
        except Exception as e:
            logger.warning(f"Failed to get GPU status: {e}")
            return None
    
    def get_loaded_models(self) -> list[ModelMemory]:
        """Get per-model VRAM from Ollama API."""
        try:
            response = httpx.get(OLLAMA_PS_URL, timeout=5)
            data = response.json()
            
            models = []
            for m in data.get("models", []):
                models.append(ModelMemory(
                    name=m["name"],
                    size_vram_bytes=m.get("size_vram", m.get("size", 0)),
                    context_length=m.get("context_length", 0),
                    parameter_size=m.get("details", {}).get("parameter_size", "?"),
                ))
            return models
        except Exception:
            return []
    
    def print_status(self) -> tuple[GPUStatus | None, list[ModelMemory]]:
        """Print combined GPU and model status."""
        gpu = self.get_gpu_status()
        models = self.get_loaded_models()
        
        print("\n┌─ GPU Monitor ────────────────────────────────────────────────────┐")
        
        if gpu:
            temp_status = f"⚠️ {gpu.temp_c}°C" if gpu.should_pause else f"{gpu.temp_c}°C"
            print(f"│ Temperature: {temp_status} (limit: {self.temp_limit}°C)")
            print(f"│ VRAM: {gpu.vram_used_gb:.1f}GB/{gpu.vram_total_gb:.1f}GB ({gpu.vram_percent:.0f}%)")
            print(f"│ GPU Util: {gpu.gpu_util}%")
        else:
            print("│ GPU monitoring unavailable")
        
        if models:
            print("├─ Active Models (Ollama) ─────────────────────────────────────────┤")
            for m in models:
                info = MODEL_INFO.get(m.name, {})
                task = info.get("task", "?")
                print(f"│ {m.name:<18} {m.size_vram_gb:>5.1f} GB  ({task})")
        
        if gpu and gpu.should_pause:
            print("│ ⚠️  PAUSING: Temperature above limit!")
        if gpu and gpu.should_warn:
            print("│ ⚠️  WARNING: VRAM usage high!")
        
        print("└───────────────────────────────────────────────────────────────────┘")
        
        return gpu, models


async def unload_unused_models(keep_models: set[str]):
    """Unload models not in the keep_models set."""
    try:
        response = httpx.get(OLLAMA_PS_URL, timeout=5)
        data = response.json()
        
        for m in data.get("models", []):
            model_name = m["name"]
            # Check if model should be kept
            should_keep = any(keep in model_name for keep in keep_models)
            
            if not should_keep:
                logger.info(f"Unloading unused model: {model_name}")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(OLLAMA_UNLOAD_URL, json={
                        "model": model_name,
                        "keep_alive": 0,  # Unload immediately
                    })
    except Exception as e:
        logger.warning(f"Failed to unload models: {e}")


async def preload_models():
    """Preload required models with a warm-up request."""
    required_models = {MODELS["tier_l0"], MODELS["tier_l2"]}
    
    logger.info(f"Preloading models: {required_models}")
    
    for model in required_models:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Simple warm-up request
                await client.post(OLLAMA_URL, json={
                    "model": model,
                    "prompt": "Ready",
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {"num_predict": 1},
                })
                logger.info(f"  Loaded: {model}")
        except Exception as e:
            logger.warning(f"Failed to preload {model}: {e}")
    
    # Unload any models we don't need
    await unload_unused_models(required_models)


# Checkpoint functions

def save_checkpoint(completed: list[str], target: str, category: str, current_index: int):
    """Save checkpoint after each wisdom."""
    checkpoint = {
        "timestamp": datetime.now().isoformat(),
        "target": target,
        "category": category,
        "completed_wisdoms": completed,
        "count": len(completed),
        "current_index": current_index,
    }
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f, indent=2)


def load_checkpoint() -> dict | None:
    """Load checkpoint if exists."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None


def clear_checkpoint():
    """Clear checkpoint file."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


# Progress display

def print_progress_bar(current: int, total: int, start_time: float, gpu: GPUStatus | None = None):
    """Print progress bar with ETA."""
    elapsed = time.time() - start_time
    if current > 0:
        eta_seconds = (elapsed / current) * (total - current)
        eta_min = int(eta_seconds // 60)
        eta_sec = int(eta_seconds % 60)
    else:
        eta_min, eta_sec = 0, 0
    
    percent = (current / total) * 100 if total > 0 else 0
    filled = int(40 * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (40 - filled)
    
    gpu_info = f" | GPU: {gpu.temp_c}°C" if gpu else ""
    print(f"\r[{bar}] {percent:.0f}% | {current}/{total} | ETA: {eta_min}m {eta_sec}s{gpu_info}    ", end="", flush=True)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


async def call_ollama(prompt: str, model: str, max_tokens: int = 2000) -> str:
    """Call Ollama API asynchronously."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
            }
        })
        response.raise_for_status()
        return response.json()["response"].strip()


async def generate_tiers_parallel(content: str, target: str, category: str) -> dict[str, str]:
    """Generate L0, L1, and L2 tiers in parallel."""
    # Select L2 prompt based on category
    if "catchphrase" in category:
        l2_prompt = L2_CATCHPHRASES_PROMPT.format(content=content, target=target)
    elif "quote" in category:
        l2_prompt = L2_QUOTES_PROMPT.format(content=content, target=target)
    else:
        l2_prompt = L2_MISLEADING_FACTS_PROMPT.format(content=content, target=target)
    
    l0_task = call_ollama(TIER_L0_PROMPT.format(content=content), MODELS["tier_l0"], max_tokens=300)
    l1_task = call_ollama(TIER_L1_PROMPT.format(content=content), MODELS["tier_l1"], max_tokens=800)
    l2_task = call_ollama(l2_prompt, MODELS["tier_l2"], max_tokens=2500)
    
    l0, l1, l2 = await asyncio.gather(l0_task, l1_task, l2_task)
    return {"l0": l0, "l1": l1, "l2": l2}


def create_frontmatter(uri: str, source: str, target: str, category: str, tier: str, tokens: int) -> str:
    """Create YAML frontmatter for a file."""
    return f"""---
uri: {uri}
source: {source}
target: {target}
category: {category}
tier: {tier}
tokens: {tokens}
generated: {datetime.now().strftime("%Y-%m-%d")}
---

"""


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:50]


def extract_fact_name(fact_text: str, index: int) -> str:
    """Extract a short name from fact text."""
    text = fact_text.strip()
    if text.lower().startswith("why "):
        text = text[4:]
    
    words = text.split()[:4]
    slug = slugify(" ".join(words))
    
    if not slug:
        slug = f"fact-{index}"
    
    return slug


def parse_enrichment_file(filepath: Path) -> tuple[list[str], dict]:
    """Parse enrichment file to extract individual wisdoms."""
    content = filepath.read_text()
    
    # Extract YAML frontmatter
    frontmatter = {}
    if content.startswith("---"):
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            yaml_text = match.group(1)
            for line in yaml_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            content = content[match.end():].strip()
    
    # Parse numbered facts (handles " 1. " and "1. " formats)
    facts = []
    # Pattern matches: optional leading spaces, number, period, space, then content
    for match in re.finditer(r'^\s*\d+\.\s+(.+?)(?=\n\s*\d+\.|\n*$)', content, re.MULTILINE | re.DOTALL):
        fact_text = match.group(1).strip()
        if fact_text and len(fact_text) > 10:
            facts.append(fact_text)
    
    # If no numbered facts, try line-by-line
    if not facts:
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                # Remove markdown formatting
                line = re.sub(r'[*_`]', '', line)
                if line:
                    facts.append(line)
    
    return facts, frontmatter


async def expand_fact(
    fact_text: str,
    fact_name: str,
    target: str,
    category: str,
    source_file: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Expand a single fact to L0/L1/L2 with new format."""
    
    logger.info(f"Expanding: {fact_name}")
    
    # Create output directory
    fact_dir = output_dir / fact_name
    fact_dir.mkdir(parents=True, exist_ok=True)
    
    # URI for Viking
    uri = f"viking://resources/enrichment/{target}/{category}/{fact_name}"
    
    # Generate L0, L1, and L2 in parallel (all via LLM now)
    tiers = await generate_tiers_parallel(fact_text, target, category)
    
    # L2 is now generated by LLM with rich "fabulous" content
    l2_content = tiers["l2"]
    
    # Estimate tokens
    l0_tokens = estimate_tokens(tiers["l0"])
    l1_tokens = estimate_tokens(tiers["l1"])
    l2_tokens = estimate_tokens(l2_content)
    
    # Generate date
    generated_date = datetime.now().strftime("%Y-%m-%d")
    
    # Write .metadata.yaml
    metadata = f"""uri: {uri}
source: {source_file}
target: {target}
category: {category}
chunk_name: {fact_name}
generated: {generated_date}
tiers:
  l0:
    file: l0.abstract
    tokens: {l0_tokens}
  l1:
    file: l1.overview
    tokens: {l1_tokens}
  l2:
    file: l2.content.md
    tokens: {l2_tokens}
"""
    
    # Write files (new format: pure content, no frontmatter)
    metadata_path = fact_dir / ".metadata.yaml"
    l0_path = fact_dir / "l0.abstract"
    l1_path = fact_dir / "l1.overview"
    l2_path = fact_dir / "l2.content.md"
    
    metadata_path.write_text(metadata)
    l0_path.write_text(tiers["l0"])
    l1_path.write_text(tiers["l1"])
    l2_path.write_text(l2_content)
    
    return {
        "name": fact_name,
        "dir": str(fact_dir),
        "tokens": {"l0": l0_tokens, "l1": l1_tokens, "l2": l2_tokens},
        "success": True,
    }


async def expand_enrichment_file(
    input_file: Path,
    output_base: Path,
    monitor: GPUMonitor | None = None,
    chunk_size: int = 10,
    start_index: int = 0,
    resume: bool = False,
) -> list[dict]:
    """Expand all facts in an enrichment file with GPU monitoring and chunking."""
    
    facts, frontmatter = parse_enrichment_file(input_file)
    
    target = frontmatter.get("target", "unknown")
    category = frontmatter.get("type", "misleading-facts")
    
    if "catchphrase" in category:
        category_dir = "catchphrases"
    elif "quote" in category:
        category_dir = "quotes"
    else:
        category_dir = "misleading-facts"
    
    output_dir = output_base / target / category_dir
    
    # Check for existing wisdoms (skip already processed)
    existing_wisdoms = set()
    if resume:
        for existing in output_dir.iterdir():
            if existing.is_dir() and (existing / ".metadata.yaml").exists():
                existing_wisdoms.add(existing.name)
    
    total_facts = len(facts)
    facts_to_process = [(i, f) for i, f in enumerate(facts) if start_index <= i and extract_fact_name(f, i) not in existing_wisdoms]
    
    logger.info(f"Processing {input_file}: {len(facts_to_process)} of {total_facts} facts (skipping {len(existing_wisdoms)} existing)")
    
    if monitor:
        monitor.print_status()
    
    start_time = time.time()
    results = []
    completed_names = list(existing_wisdoms)
    
    for chunk_start in range(0, len(facts_to_process), chunk_size):
        chunk = facts_to_process[chunk_start:chunk_start + chunk_size]
        
        for i, fact in chunk:
            fact_name = extract_fact_name(fact, i)
            
            # Check GPU status
            if monitor:
                gpu = monitor.get_gpu_status()
                if gpu and gpu.should_pause:
                    print(f"\n⚠️ GPU temp {gpu.temp_c}°C >= {monitor.temp_limit}°C, pausing 30s...")
                    await asyncio.sleep(30)
                elif gpu and gpu.should_warn:
                    logger.warning(f"VRAM usage {gpu.vram_percent:.0f}% >= {monitor.vram_warn_percent}%")
            
            # Process fact
            try:
                result = await expand_fact(
                    fact_text=fact,
                    fact_name=fact_name,
                    target=target,
                    category=category_dir,
                    source_file=str(input_file),
                    output_dir=output_dir,
                )
                results.append(result)
                completed_names.append(fact_name)
                
                # Save checkpoint
                save_checkpoint(completed_names, target, category_dir, i)
                
                # Progress bar
                if monitor:
                    gpu = monitor.get_gpu_status()
                    print_progress_bar(len(results), len(facts_to_process), start_time, gpu)
                else:
                    print_progress_bar(len(results), len(facts_to_process), start_time)
                
            except Exception as e:
                logger.error(f"\nFailed to process {fact_name}: {e}")
                results.append({"name": fact_name, "success": False, "error": str(e)})
        
        # Brief pause between chunks
        if chunk_start + chunk_size < len(facts_to_process):
            print(f"\n\nChunk complete ({len(results)}/{len(facts_to_process)}). Brief pause...")
            await asyncio.sleep(2)
            if monitor:
                monitor.print_status()
    
    print(f"\n\n{'='*60}")
    print(f"Category complete: {len([r for r in results if r.get('success')])} succeeded")
    print(f"Total time: {(time.time() - start_time)/60:.1f} minutes")
    
    return results


async def test_single_fact():
    """Test with a single fact."""
    test_fact = "Why NASA has never shown a real photo of Earth. Period."
    
    logger.info("Testing single fact expansion...")
    
    result = await expand_fact(
        fact_text=test_fact,
        fact_name="nasa-photos-cgi-test",
        target="flat-earth",
        category="misleading-facts",
        source_file="test",
        output_dir=FACTS_DIR,
    )
    
    logger.info(f"Test result: {result}")
    return result


async def expand_with_options(
    target: str | None = None,
    category: str | None = None,
    chunk_size: int = 10,
    gpu_monitor: bool = False,
    temp_limit: int = 80,
    vram_warn: int = 90,
    resume: bool = False,
    start: int = 0,
    end: int | None = None,
):
    """Expand with GPU monitoring and chunking options."""
    
    monitor = GPUMonitor(temp_limit, vram_warn) if gpu_monitor else None
    
    print("\n" + "="*60)
    print("WISDOM EXPANSION PIPELINE")
    print("="*60)
    print(f"  Models: {MODELS['tier_l0']} (L0/L1), {MODELS['tier_l2']} (L2)")
    if gpu_monitor:
        print("  GPU Monitor: ENABLED")
        print(f"  Temperature limit: {temp_limit}°C")
        print(f"  VRAM warning: {vram_warn}%")
    else:
        print("  GPU Monitor: disabled")
    print(f"  Chunk size: {chunk_size}")
    print("="*60)
    
    # Preload required models and unload unused ones
    await preload_models()
    
    if monitor:
        monitor.print_status()
    
    # Find files to process
    files_to_process = []
    for enrichment_file in ENRICHMENT_DIR.rglob("*.md"):
        _, fm = parse_enrichment(enrichment_file)
        file_target = fm.get("target", "unknown")
        file_category = fm.get("type", "misleading-facts")
        
        if target and file_target != target:
            continue
        if category and category not in file_category:
            continue
        
        files_to_process.append(enrichment_file)
    
    if not files_to_process:
        logger.error("No files match criteria")
        return []
    
    logger.info(f"Found {len(files_to_process)} file(s) to process")
    
    # Check checkpoint for resume
    if resume:
        checkpoint = load_checkpoint()
        if checkpoint:
            print(f"\nResuming from checkpoint: {checkpoint['count']} wisdoms already done")
            print(f"  Target: {checkpoint['target']}, Category: {checkpoint['category']}")
    
    all_results = []
    for enrichment_file in files_to_process:
        print(f"\n{'='*60}")
        print(f"Processing: {enrichment_file.name}")
        print("="*60)
        
        try:
            results = await expand_enrichment_file(
                enrichment_file,
                FACTS_DIR,
                monitor=monitor,
                chunk_size=chunk_size,
                start_index=start,
                resume=resume,
            )
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Failed to process {enrichment_file}: {e}")
        
        # Clear checkpoint after successful completion
        clear_checkpoint()
    
    # Final summary
    success = sum(1 for r in all_results if r.get("success"))
    failed = len(all_results) - success
    
    print(f"\n{'='*60}")
    print("EXPANSION COMPLETE")
    print("="*60)
    print(f"Total: {len(all_results)}")
    print(f"Succeeded: {success}")
    print(f"Failed: {failed}")
    
    if all_results:
        l0_tokens = [r['tokens']['l0'] for r in all_results if r.get('tokens')]
        l1_tokens = [r['tokens']['l1'] for r in all_results if r.get('tokens')]
        l2_tokens = [r['tokens']['l2'] for r in all_results if r.get('tokens')]
        
        if l0_tokens:
            print("\nToken Stats:")
            print(f"  L0: avg {sum(l0_tokens)//len(l0_tokens)}, max {max(l0_tokens)}")
            print(f"  L1: avg {sum(l1_tokens)//len(l1_tokens)}, max {max(l1_tokens)}")
            print(f"  L2: avg {sum(l2_tokens)//len(l2_tokens)}, max {max(l2_tokens)}")
    
    return all_results


def parse_enrichment(filepath: Path) -> tuple[list[str], dict]:
    """Parse enrichment file (alias for compatibility)."""
    return parse_enrichment_file(filepath)


async def expand_all():
    """Expand all enrichment files."""
    return await expand_with_options(gpu_monitor=True)


def main():
    parser = argparse.ArgumentParser(description="Expand enrichment content to L0/L1/L2")
    parser.add_argument("--test", action="store_true", help="Test with single fact")
    parser.add_argument("--all", action="store_true", help="Process all enrichment files")
    parser.add_argument("--target", help="Process specific target only")
    parser.add_argument("--category", help="Process specific category only")
    parser.add_argument("--file", help="Process specific file only")
    parser.add_argument("--chunk-size", type=int, default=10, help="Wisdoms per chunk")
    parser.add_argument("--gpu-monitor", action="store_true", help="Enable GPU monitoring")
    parser.add_argument("--temp-limit", type=int, default=80, help="Temperature pause limit (°C)")
    parser.add_argument("--vram-warn", type=int, default=90, help="VRAM warning threshold (%)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--start", type=int, default=0, help="Start from fact index")
    parser.add_argument("--end", type=int, help="End at fact index")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_single_fact())
    elif args.all:
        asyncio.run(expand_with_options(
            gpu_monitor=args.gpu_monitor,
            chunk_size=args.chunk_size,
            temp_limit=args.temp_limit,
            vram_warn=args.vram_warn,
            resume=args.resume,
        ))
    elif args.target or args.category:
        asyncio.run(expand_with_options(
            target=args.target,
            category=args.category,
            chunk_size=args.chunk_size,
            gpu_monitor=args.gpu_monitor,
            temp_limit=args.temp_limit,
            vram_warn=args.vram_warn,
            resume=args.resume,
            start=args.start,
            end=args.end,
        ))
    elif args.file:
        input_file = Path(args.file)
        if input_file.exists():
            asyncio.run(expand_enrichment_file(input_file, FACTS_DIR))
        else:
            logger.error(f"File not found: {input_file}")
            sys.exit(1)
    else:
        parser.print_help()
        parser.print_help()


if __name__ == "__main__":
    main()
