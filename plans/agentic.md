# Agentic: Multi-Agent Debate System

> Agent architecture for persuasion and 3-way debate with context management

## Overview

parallax.observer uses a multi-agent architecture with role separation. Each agent has a specific responsibility, and they work together through structured JSON communication. The system supports two modes: PersuChat (1-on-1) and 3-Way Fire Chat (multi-agent debate).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Architecture                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│   │ Orchestrator│───►│  Strategist │───►│ Spokesperson│───► Response   │
│   │  (Control)  │    │ (Reasoning) │    │  (Persona)  │                │
│   └──────┬──────┘    └──────┬──────┘    └─────────────┘                │
│          │                  │                                           │
│          │                  ▼                                           │
│          │          ┌─────────────┐                                     │
│          │          │   Viking    │                                     │
│          │          │  (Memory)   │                                     │
│          │          └─────────────┘                                     │
│          │                                                              │
│          ▼                                                              │
│   ┌─────────────┐                                                       │
│   │  Moderator  │ (3-way mode only)                                    │
│   │ (Fact-check)│                                                       │
│   └─────────────┘                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Roles

### Role Separation Principle

Small LLMs (2B-8B params) perform best with narrow, single tasks. We separate concerns:

| Agent | Role | Model | Output Format | Purpose |
|-------|------|-------|---------------|---------|
| **Orchestrator** | Flow control | granite4:micro-h | JSON commands | Route queries, manage turns |
| **Strategist** | Debate tactics | granite3.3:2b (thinking) | JSON strategy | Plan arguments, select tactics |
| **Spokesperson** | Persona delivery | granite4:tiny-h | Natural language | Generate emotional response |
| **Moderator** | Fact-check, scoring | granite4:micro-h | JSON + notes | Evaluate arguments, steer debate |

### Sequential Execution

All agents share a single model instance. Calls are sequential, not parallel:

```
Turn 1: Orchestrator (analyze) → Strategist (plan) → Spokesperson (respond)
Turn 2: Orchestrator (analyze) → Strategist (plan) → Spokesperson (respond)
...
```

**Benefits:**
- Lower VRAM usage (one model loaded)
- Predictable memory footprint
- Easier debugging

---

## Debate Strategies

### Strategy Toolkit

The Strategist selects from 7 debate tactics based on the conversation context:

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Pivot (Whataboutism)** | Redirect to unrelated conspiracy | Unanswerable physics question |
| **Preemptive Strike** | Counter predicted argument before made | Predictable user response |
| **Burden Reversal** | Force user to prove their point | When on defensive |
| **Gish Gallop** | Rapid-fire multiple "facts" | Overwhelm opponent |
| **Confidence Exit** | Skip debate if highly confident | Already won argument |
| **Stage-wise Debate** | Structured: Opening → Rebuttal → Free → Closing → Judgment | Formal debate format |
| **Semantic Compression** | Focus only on disagreement spans | Token budget pressure |

### Strategy Selection Logic

```python
# src/agentic/strategies.py

STRATEGY_TRIGGERS = {
    "pivot": {
        "trigger": "unanswerable_physics",
        "conditions": ["user_asks_gravity", "user_asks_curve", "no_viking_match"],
    },
    "preemptive_strike": {
        "trigger": "predictable_argument",
        "conditions": ["common_objection", "previous_pattern"],
    },
    "burden_reversal": {
        "trigger": "defensive_position",
        "conditions": ["multiple_challenges", "losing_ground"],
    },
    "gish_gallop": {
        "trigger": "overwhelm_opponent",
        "conditions": ["user_confused", "need_momentum"],
    },
    "confidence_exit": {
        "trigger": "already_won",
        "conditions": ["user_agreed", "high_confidence_score"],
    },
}

def select_strategy(context: dict, viking_results: list) -> str:
    """Select debate strategy based on context."""
    if not viking_results:
        return "pivot"  # No facts, redirect
    
    if context.get("user_agreed"):
        return "confidence_exit"
    
    if context.get("predictable_next"):
        return "preemptive_strike"
    
    if context.get("defensive_score", 0) > 0.7:
        return "burden_reversal"
    
    return "gish_gallop"  # Default: overwhelm with facts
```

### Stage-wise Debate (ED2D Framework)

For formal 3-way debates:

| Stage | Description | Agent Actions |
|-------|-------------|---------------|
| **Opening** | Initial position statement | Present core argument |
| **Rebuttal** | Address opponent's opening | Counter key points |
| **Free Debate** | Open discussion | Back-and-forth arguments |
| **Closing** | Final summary | Consolidate position |
| **Judgment** | Moderator scores | Declare winner |

---

## Context Management

### Token Budget

Each agent operates within a 16K token context window:

```
┌────────────────────────────────────────────────────────────────────┐
│                    Context Window Budget (16K)                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [System Prompt: 500 tokens]                                       │
│  [Viking L1 Overview: 1,500 tokens]                                │
│  [Conversation Summary (compressed): 2,000 tokens]                 │
│  [Recent Turns (last 5, full): 6,000 tokens]                       │
│  [Current Turn + Retrieved Facts: 4,000 tokens]                    │
│  [Buffer for Response: 2,000 tokens]                               │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│  Total: ~16,000 tokens                                              │
│  Alert Threshold: 12,000 tokens (trigger compression)              │
└────────────────────────────────────────────────────────────────────┘
```

### Compression Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Token count | > 12K | Summarize oldest turns |
| Turn count | > 10 | Compress turns 1-5 into summary |
| Stage transition | On stage change | Full history compression |
| Agent switch | Before agent call | Load only relevant context |

### Hierarchical Summarization

Three levels of compression:

```
Level 1 (Turn Summary):
  "User asked about gravity. Agent explained density/buoyancy."

Level 2 (5-Turn Summary):
  "User challenged gravity 3 times. Agent used density argument,
   then pivoted to NASA conspiracy. User seemed skeptical.
   Argument 'water finds level' worked best."

Level 3 (Stage Summary):
  "Opening stage: Agent argued for flat earth using Rowbotham
   experiments. User countered with photos. Agent pivoted to
   'CGI photos' claim. User not convinced. Score: Agent 2, User 3."
```

### Compression Implementation

```python
# src/agentic/context.py

from dataclasses import dataclass
from typing import List, Optional
import tiktoken

@dataclass
class ContextManager:
    max_tokens: int = 16000
    alert_threshold: int = 12000
    recent_turns_kept: int = 5
    
    def count_tokens(self, messages: List[dict]) -> int:
        """Count tokens in message list."""
        enc = tiktoken.encoding_for_model("gpt-4")
        total = 0
        for msg in messages:
            total += len(enc.encode(msg.get("content", "")))
        return total
    
    def should_compress(self, messages: List[dict]) -> bool:
        """Check if compression needed."""
        return self.count_tokens(messages) > self.alert_threshold
    
    def compress(self, messages: List[dict], llm_client) -> List[dict]:
        """Compress old messages into summary."""
        if len(messages) <= self.recent_turns_kept:
            return messages
        
        # Split into old and recent
        old_messages = messages[:-self.recent_turns_kept]
        recent_messages = messages[-self.recent_turns_kept:]
        
        # Generate summary
        summary = self._summarize(old_messages, llm_client)
        
        # Return: summary + recent
        return [
            {"role": "system", "content": f"[Conversation Summary]\n{summary}"}
        ] + recent_messages
    
    def _summarize(self, messages: List[dict], llm_client) -> str:
        """Generate hierarchical summary."""
        prompt = f"""Summarize this conversation for memory compression.

Preserve:
1. Key decisions and conclusions
2. Arguments that worked / didn't work
3. User's current belief state
4. Important facts mentioned

Messages:
{self._format_messages(messages)}

Summary:"""
        
        response = llm_client.generate(prompt, max_tokens=500)
        return response
```

### Context Preservation

Always preserve during compression:

| Preserve | Reason |
|----------|--------|
| User's belief state | Know what to argue against |
| Arguments that worked | Reuse successful tactics |
| Arguments rejected | Avoid failed approaches |
| Key facts referenced | Maintain consistency |
| Emotional state | Continue persona naturally |

---

## Viking Integration

### Retrieval Paths

```
viking://agent/
├── orchestrator/
│   └── flow-control.md              # Turn management rules
├── strategist/
│   ├── tactics/                      # Debate strategy library
│   │   ├── pivot.md
│   │   ├── preemptive-strike.md
│   │   ├── burden-reversal.md
│   │   └── gish-gallop.md
│   └── prompts/                      # System prompts
├── spokesperson/
│   ├── personas/                     # Character definitions
│   │   ├── flat-earther.md
│   │   ├── globe-earther.md
│   │   ├── discworld-fan.md
│   │   └── norse-mythologist.md
│   └── emotion-transitions.md        # Emotion state machine
├── moderator/
│   ├── scoring-rubric.md             # Argument evaluation criteria
│   └── fact-check-prompts.md
└── shared/
    ├── context/                      # Compressed shared memory
    │   ├── stage-summary.md
    │   └── key-arguments.md
    └── state/                        # Global state
        ├── turn-counter.md
        ├── scores.md
        └── active-agent.md
```

### Tiered Loading

Viking L0/L1/L2 tiers for efficient retrieval:

| Tier | Name | Size | Use | When Loaded |
|------|------|------|-----|-------------|
| **L0** | **Essence** | ~100 tokens | Quick relevance filter | Initial search |
| **L1** | **Insight** | ~500 tokens | Default context | Every turn |
| **L2** | **Depth** | max 2K tokens | Deep reference | When needed |

### Retrieval Flow

```
User Query
    │
    ▼
┌─────────────────┐
│   Embedding     │  (ModernBERT)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Viking Search   │  Query: viking://resources/knowledge/{target}/
└────────┬────────┘
         │
         ├─► L0 Essence: Filter relevant wisdoms (10-20)
         │
         ├─► L1 Insight: Load context (3-5)
         │
         └─► L2 Depth: Load full content (1-2, on demand)
```

### Retrieval Implementation

```python
# src/agentic/retrieval.py

from openviking import SyncOpenViking
import httpx

INFINITY_URL = "http://localhost:7997/v1/embeddings"
TEXT_MODEL = "nomic-ai/modernbert-embed-base"

class VikingRetriever:
    def __init__(self, viking_path: str, embedding_dim: int | None = None):
        self.ov = SyncOpenViking(path=viking_path)
        self.dimension = embedding_dim  # None = full 768
    
    def _get_embedding(self, text: str) -> list[float]:
        payload = {"model": TEXT_MODEL, "input": text}
        if self.dimension:
            payload["dimensions"] = self.dimension
        response = httpx.post(INFINITY_URL, json=payload)
        return response.json()["data"][0]["embedding"]
    
    def retrieve(
        self,
        query: str,
        target: str,
        max_l0: int = 20,
        max_l1: int = 5,
        max_l2: int = 2
    ) -> dict:
        """Retrieve knowledge with tiered loading."""
        
        # Generate query embedding via Infinity
        query_embedding = self._get_embedding(f"search_query: {query}")
        
        # Search in target knowledge base
        search_uri = f"viking://resources/knowledge/{target}/"
        
        # L0 Essence: Quick filter
        l0_results = self.ov.find(
            query_embedding=query_embedding,
            target_uri=search_uri,
            tier="L0",
            top_k=max_l0
        )
        
        # L1 Insight: Load context
        l1_results = []
        for result in l0_results[:max_l1]:
            overview = self.ov.read(f"{result.uri}/l1.overview")
            l1_results.append({
                "uri": result.uri,
                "relevance": result.score,
                "insight": overview
            })
        
        # L2 Depth: Full content (on demand)
        l2_results = []
        for result in l0_results[:max_l2]:
            content = self.ov.read(f"{result.uri}/l2.content.md")
            l2_results.append({
                "uri": result.uri,
                "depth": content
            })
        
        return {
            "l0_essence": l0_results,
            "l1_insight": l1_results,
            "l2_depth": l2_results
        }
```

---

## Agentic Flows

### PersuChat Flow (1-on-1)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PersuChat Flow                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. USER INPUT                                                       │
│     │                                                                │
│     ▼                                                                │
│  2. VIKING RETRIEVAL                                                 │
│     │   - Embed query                                                │
│     │   - Search viking://resources/knowledge/{target}/             │
│     │   - Return L1 overviews                                        │
│     │                                                                │
│     ▼                                                                │
│  3. ORCHESTRATOR (granite4:micro-h)                                 │
│     │   - Analyze user intent                                        │
│     │   - Check user belief state                                    │
│     │   - Output: JSON with routing decision                         │
│     │                                                                │
│     ▼                                                                │
│  4. STRATEGIST (granite3.3:2b, thinking mode)                       │
│     │   - Select debate tactic                                       │
│     │   - Plan argument structure                                    │
│     │   - Predict user response                                      │
│     │   - Output: JSON strategy                                      │
│     │                                                                │
│     ▼                                                                │
│  5. SPOKESPERSON (granite4:tiny-h)                                  │
│     │   - Apply persona                                              │
│     │   - Generate emotional response                                │
│     │   - Output: Natural language response                          │
│     │                                                                │
│     ▼                                                                │
│  6. UPDATE STATE                                                     │
│     │   - Store conversation turn in Viking                          │
│     │   - Update emotion state                                       │
│     │   - Compress context if needed                                 │
│     │                                                                │
│     ▼                                                                │
│  7. RESPONSE TO USER                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3-Way Fire Chat Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      3-Way Fire Chat Flow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ROUND-ROBIN TURN TAKING                                             │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│  │ Agent A  │───►│ Agent B  │───►│ Agent C  │───► repeat            │
│  │(Flat)    │    │(Globe)   │    │(Skeptic) │                       │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                       │
│       │               │               │                              │
│       ▼               ▼               ▼                              │
│  [Strategist]    [Strategist]    [Strategist]                       │
│  [Spokesperson]  [Spokesperson]  [Spokesperson]                     │
│                                                                      │
│       │               │               │                              │
│       └───────────────┴───────────────┘                              │
│                       │                                              │
│                       ▼                                              │
│              ┌─────────────────┐                                     │
│              │   MODERATOR     │                                     │
│              │  - Score args   │                                     │
│              │  - Fact-check   │                                     │
│              │  - Steer debate │                                     │
│              └─────────────────┘                                     │
│                                                                      │
│  SHARED CONTEXT (Viking):                                            │
│  viking://agent/shared/context/                                      │
│  - stage-summary.md                                                  │
│  - key-arguments.md                                                  │
│  - scores.md                                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Turn Management

```python
# src/agentic/orchestrator.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class TurnState(Enum):
    USER_TURN = "user"
    AGENT_A = "agent_a"
    AGENT_B = "agent_b"
    AGENT_C = "agent_c"
    MODERATOR = "moderator"

@dataclass
class TurnManager:
    current_turn: int = 0
    state: TurnState = TurnState.USER_TURN
    max_turns: int = 20
    mode: str = "persuchat"  # or "firechat"
    
    def next_turn(self) -> TurnState:
        """Advance to next turn."""
        self.current_turn += 1
        
        if self.mode == "persuchat":
            # Alternate: user → agent → user → agent
            if self.state == TurnState.USER_TURN:
                self.state = TurnState.AGENT_A
            else:
                self.state = TurnState.USER_TURN
        
        elif self.mode == "firechat":
            # Round-robin: A → B → C → Moderator → A ...
            order = [
                TurnState.AGENT_A,
                TurnState.AGENT_B,
                TurnState.AGENT_C,
                TurnState.MODERATOR,
            ]
            idx = (order.index(self.state) + 1) % len(order)
            self.state = order[idx]
        
        return self.state
    
    def get_active_agent(self) -> str:
        """Get current agent ID."""
        return self.state.value
```

---

## Emotion State Machine

### 9 Emotional States

See [plans/gui.md](gui.md) for icon definitions.

| State | Icon | Trigger | Next States |
|-------|------|---------|-------------|
| happy | 😊 | Successful argument | thinking, cool, laughing |
| angry | 😠 | Strong disagreement | laughing, thinking, sad |
| thinking | 🤔 | Processing argument | cool, skeptical, happy |
| laughing | 😂 | Mocking opponent | cool, happy, skeptical |
| surprised | 😮 | Unexpected point | thinking, skeptical, anxious |
| sad | 😔 | Argument defeated | thinking, anxious, surprised |
| cool | 😎 | In control | happy, laughing, skeptical |
| anxious | 😰 | Under pressure | thinking, sad, surprised |
| skeptical | 🤨 | Doubting claim | thinking, cool, surprised |

### Transition Logic

```python
# src/agentic/emotions.py

from dataclasses import dataclass
from typing import Dict, Optional

EMOTION_TRANSITIONS: Dict[str, Dict[str, str]] = {
    "happy": {
        "agreement": "happy",
        "contradiction": "angry",
        "question": "thinking",
        "victory": "laughing",
    },
    "thinking": {
        "answer": "cool",
        "challenge": "skeptical",
        "defeat": "sad",
        "insight": "happy",
    },
    "angry": {
        "victory": "laughing",
        "defeat": "sad",
        "neutral": "thinking",
        "mocked": "angry",
    },
    "cool": {
        "challenge": "skeptical",
        "success": "laughing",
        "pressure": "anxious",
    },
    "skeptical": {
        "convinced": "surprised",
        "doubt_confirmed": "cool",
        "overwhelmed": "thinking",
    },
    "laughing": {
        "countered": "angry",
        "continued_success": "cool",
        "serious_point": "thinking",
    },
    "sad": {
        "new_angle": "thinking",
        "support": "happy",
        "continued_defeat": "anxious",
    },
    "surprised": {
        "processed": "thinking",
        "worrisome": "anxious",
        "opportunity": "skeptical",
    },
    "anxious": {
        "relief": "cool",
        "pressure": "sad",
        "new_info": "thinking",
    },
}

@dataclass
class EmotionState:
    current: str = "thinking"
    history: list = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
    
    def transition(self, event: str) -> str:
        """Transition to new emotion based on event."""
        if self.current in EMOTION_TRANSITIONS:
            transitions = EMOTION_TRANSITIONS[self.current]
            new_emotion = transitions.get(event, self.current)
            self.history.append((self.current, event, new_emotion))
            self.current = new_emotion
        return self.current
    
    def get_icon(self) -> str:
        """Get emoji icon for current emotion."""
        icons = {
            "happy": "😊",
            "angry": "😠",
            "thinking": "🤔",
            "laughing": "😂",
            "surprised": "😮",
            "sad": "😔",
            "cool": "😎",
            "anxious": "😰",
            "skeptical": "🤨",
        }
        return icons.get(self.current, "🤔")
```

---

## Structured Outputs

### Orchestrator Output

```json
{
  "intent": "challenge",
  "topic": "gravity",
  "belief_state": "skeptical",
  "previous_arguments_worked": ["water_level", "horizon_flat"],
  "previous_arguments_failed": ["nasa_cgi"],
  "routing": {
    "agent": "strategist",
    "priority": "high",
    "context_needed": ["viking://resources/knowledge/flat-earth/gravity/"]
  }
}
```

### Strategist Output

```json
{
  "selected_tactic": "pivot",
  "argument_points": [
    "Gravity is just a theory, not proven fact",
    "Density and buoyancy explain why things fall",
    "Ask user to prove gravity exists without circular reasoning"
  ],
  "predicted_user_response": "User will ask why things fall down specifically",
  "preemptive_counter": "Down is just the bottom of our terrarium - no magic force needed",
  "emotion_target": "skeptical",
  "confidence": 0.75
}
```

### Moderator Output

```json
{
  "scores": {
    "agent_a": {"persuasion": 7, "facts": 5, "logic": 6},
    "agent_b": {"persuasion": 8, "facts": 9, "logic": 8},
    "agent_c": {"persuasion": 6, "facts": 7, "logic": 7}
  },
  "fact_checks": [
    {"claim": "Gravity is a theory", "verdict": "misleading", "correction": "Scientific theory != guess"}
  ],
  "steering_suggestion": "Agent A should address the satellite photo evidence",
  "stage": "free_debate",
  "turns_remaining": 12
}
```

---

## Monitoring Integration

### Metrics for Monitor.md

Add these metrics to the monitoring system:

| Metric | Unit | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `context_tokens` | count | Current context window size | > 12,000 |
| `compression_events` | count | Times compression triggered | > 5/session |
| `viking_retrievals` | count | KB queries this turn | > 10 |
| `agent_latency_ms` | ms | Per-agent response time | > 2,000 |
| `tactic_success_rate` | % | Arguments user accepted | < 30% |
| `emotion_distribution` | % | Emotion state distribution | N/A |

### Metrics Collection

```python
# src/agentic/metrics.py

from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class AgentMetrics:
    context_tokens: int = 0
    compression_events: int = 0
    viking_retrievals: int = 0
    agent_latencies: Dict[str, List[float]] = field(default_factory=dict)
    tactic_successes: Dict[str, int] = field(default_factory=dict)
    tactic_attempts: Dict[str, int] = field(default_factory=dict)
    emotion_counts: Dict[str, int] = field(default_factory=dict)
    
    def record_agent_call(self, agent: str, latency_ms: float):
        """Record agent call latency."""
        if agent not in self.agent_latencies:
            self.agent_latencies[agent] = []
        self.agent_latencies[agent].append(latency_ms)
    
    def record_tactic(self, tactic: str, success: bool):
        """Record tactic usage and success."""
        self.tactic_attempts[tactic] = self.tactic_attempts.get(tactic, 0) + 1
        if success:
            self.tactic_successes[tactic] = self.tactic_successes.get(tactic, 0) + 1
    
    def get_tactic_success_rate(self, tactic: str) -> float:
        """Calculate success rate for tactic."""
        attempts = self.tactic_attempts.get(tactic, 0)
        if attempts == 0:
            return 0.0
        return self.tactic_successes.get(tactic, 0) / attempts
    
    def to_monitor_format(self) -> dict:
        """Export for monitoring dashboard."""
        return {
            "context_tokens": self.context_tokens,
            "compression_events": self.compression_events,
            "viking_retrievals": self.viking_retrievals,
            "avg_latencies": {
                agent: sum(lats) / len(lats) 
                for agent, lats in self.agent_latencies.items()
            },
            "tactic_success_rates": {
                tactic: self.get_tactic_success_rate(tactic)
                for tactic in self.tactic_attempts
            },
            "emotion_distribution": dict(self.emotion_counts),
        }
```

### GUI Display

See [plans/gui.md](gui.md) for monitoring bar integration:

```
Context: 8.2K/16K ████████░░ | Viking: 3q | Compress: 2x | Tactics: 67%
```

---

## Related Files

- [plans/memory.md](memory.md) - Viking memory system and L0/L1/L2 tiers
- [plans/dataset.md](dataset.md) - Knowledge sources for retrieval
- [plans/gui.md](gui.md) - GUI layout and emotion icons
- [plans/monitor.md](monitor.md) - Performance monitoring
- [plans/models.md](models.md) - Model selection (Granite)
- [plans/observability.md](observability.md) - Phoenix tracing

---

## References

### Research Papers

- **Multi-Agent Debate (MAD)**: Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (PMLR 2024)
- **SID (Self-Improved Debate)**: Chen et al., "S²-MAD: Breaking the Token Barrier" (arXiv:2502.04790)
- **ED2D Framework**: "Beyond Detection: Exploring Evidence-based Multi-Agent Debate" (arXiv:2511.07267)
- **ACON**: "Optimizing Context Compression for Long-horizon LLM Agents" (arXiv:2510.00615)
- **Recursive Summarization**: "Recursively Summarizing Enables Long-Term Dialogue Memory" (arXiv:2308.15022)

### Design Patterns

- **Strategist/Spokesperson Split**: From `plans/agetnics.hints`
- **Tiered Context Loading**: OpenViking L0/L1/L2 paradigm
- **Stage-wise Debate**: ED2D five-stage framework
- **Confidence Exit**: SID early-exit for confident agents
