# GUI: Terminal-Style Web Interface

> Web-based terminal UI with real-time monitoring and multi-agent chat

## Overview

parallax.observer features a terminal-style web interface with two operational modes: PersuChat (1-on-1 persuasion) and 3-Way Fire Chat (multi-agent debate). A dedicated monitoring bar at the top shows real-time GPU/system metrics.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [MONITORING BAR - 2-4 lines]                                        │
│ GPU: 87% | VRAM: 4.2GB | Temp: 72°C | Power: 285W | 124 tok/s     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                     [MAIN CONTENT AREA]                            │
│                                                                     │
│   Mode 1: PersuChat (1-on-1)        Mode 2: 3-Way Fire Chat       │
│                                                                     │
│   ┌─────────────────────┐          ┌─────────┬─────────┬─────────┐ │
│   │                     │          │ Agent A │ Agent B │ Agent C │ │
│   │   User vs Agent     │          │   😊    │   😠    │   🤔    │ │
│   │                     │          ├─────────┼─────────┼─────────┤ │
│   │   [Chat History]    │          │         │         │         │ │
│   │                     │          │  Chat   │  Chat   │  Chat   │ │
│   │                     │          │ History │ History │ History │ │
│   │                     │          │         │         │         │ │
│   └─────────────────────┘          └─────────┴─────────┴─────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ [INPUT AREA]                                                        │
│ > _                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layout Structure

### Sections

| Section | Height | Description |
|---------|--------|-------------|
| **Monitoring Bar** | 2-4 lines | Real-time GPU/system metrics |
| **Main Content** | Flexible | Chat area (mode-dependent) |
| **Input Area** | 2-3 lines | User input with prompt |
| **Status Bar** | 1 line | Mode indicator, connection status |

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `< 768px` | Single column, monitoring collapsed |
| `768px - 1024px` | 2-column for 3-way chat |
| `> 1024px` | Full 4-panel layout with moderator |

---

## Monitoring Bar

### Location

Top 2-4 lines of the interface, always visible.

### Cross-Link

See [plans/monitor.md](monitor.md) for backend implementation.

### Display Format

```
┌─────────────────────────────────────────────────────────────────────┐
│ [GPU] RTX 3080 | Util: 87% | VRAM: 4.2/10GB | Temp: 72°C | Pwr: 285W│
│ [LLM] Model: granite3.3:2b | Tokens: 1,247 | Speed: 154 tok/s      │
│ [APP] Requests: 23 | Latency: 890ms (p95: 1.2s) | Errors: 0        │
│ [CTX] Context: 8.2K/16K | Viking: 3 queries | Compressed: 2x       │
└─────────────────────────────────────────────────────────────────────┘
```

### Compact Mode (2 lines)

```
┌─────────────────────────────────────────────────────────────────────┐
│ GPU: 87% ████████ | VRAM: 42% ████░░░░ | Temp: 72°C | 285W/320W   │
│ LLM: granite3.3:2b | 154 tok/s | 23 req | 890ms avg | CTX: 8.2K   │
└─────────────────────────────────────────────────────────────────────┘
```

### Metrics Displayed

| Category | Metrics | Update Rate |
|----------|---------|-------------|
| GPU | utilization, VRAM, temperature, power | 1s |
| LLM | model, tokens, speed | Per request |
| App | requests, latency, errors | Per request |
| Context | context tokens, viking queries, compression count | Per request |

See [plans/agentic.md](agentic.md) for context management details.

### Color Coding

| State | Color | Condition |
|-------|-------|-----------|
| Normal | Green | GPU < 80%, Temp < 75°C |
| Warning | Yellow | GPU 80-90%, Temp 75-85°C |
| Critical | Red | GPU > 90%, Temp > 85°C |

---

## Operational Modes

### Mode 1: PersuChat (1-on-1)

Single user vs single AI agent in a persuasion dialogue.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [MONITORING BAR]                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║                    PERSUCHAT MODE                             ║ │
│  ║              User vs Samuel (Persuasion Agent)                ║ │
│  ╠═══════════════════════════════════════════════════════════════╣ │
│  ║                                                               ║ │
│  ║  [😊 Samuel - Neutral]                                        ║ │
│  ║                                                               ║ │
│  ║  Samuel: "Have you considered that water always finds         ║ │
│  ║          its level? This is observable proof that the         ║ │
│  ║          Earth's surface is fundamentally flat..."            ║ │
│  ║                                                               ║ │
│  ║  ───────────────────────────────────────────────────────────  ║ │
│  ║                                                               ║ │
│  ║  User: "But what about ships disappearing over the horizon?"  ║ │
│  ║                                                               ║ │
│  ║  [🤔 Samuel - Thinking]                                       ║ │
│  ║                                                               ║ │
│  ║  Samuel: "Ah, an excellent question! That's actually due      ║ │
│  ║          to perspective, not curvature. Let me explain..."    ║ │
│  ║                                                               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ > Your response: _                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Mode 2: 3-Way Fire Chat

Three AI agents debate each other with emotional reactions.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [MONITORING BAR]                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                         3-WAY FIRE CHAT                             │
├────────────────────┬────────────────────┬───────────────────────────┤
│                    │                    │                           │
│   AGENT A          │   AGENT B          │   AGENT C                 │
│   "Flat Earther"   │   "Globe Earther"  │   "Moderator"             │
│                    │                    │                           │
│   [😠 Animated]    │   [😂 Animated]    │   [🤔 Animated]           │
│                    │                    │                           │
│   ─────────────    │   ─────────────    │   ────────────────        │
│                    │                    │                           │
│   "The horizon    │   "If Earth is     │   "Both of you have       │
│    is flat! I've   │    flat, how do    │    valid points, but      │
│    proven it with  │    you explain     │    let's examine the      │
│    my camera!"     │    sunsets?!"      │    evidence..."           │
│                    │                    │                           │
│   ─────────────    │   ─────────────    │   ────────────────        │
│                    │                    │                           │
│   [History...]     │   [History...]     │   [History...]            │
│                    │                    │                           │
├────────────────────┴────────────────────┴───────────────────────────┤
│ [MODERATOR PANEL - Optional 4th Panel]                              │
│ Moderator notes, fact-checking, and steering suggestions            │
├─────────────────────────────────────────────────────────────────────┤
│ > Observer input (or press Enter to continue): _                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Emotional Icons

### 9 Emotional States

Each agent displays an animated emoji face reflecting their emotional state. The emotion changes based on the conversation context and persuasion dynamics.

| State | Icon | Name | Trigger |
|-------|------|------|---------|
| 1 | 😊 | Happy | Successful argument, agreement |
| 2 | 😠 | Angry | Contradiction, strong disagreement |
| 3 | 🤔 | Thinking | Processing complex argument |
| 4 | 😂 | Laughing | Mocking opponent, confident |
| 5 | 😮 | Surprised | Unexpected point raised |
| 6 | 😔 | Sad | Argument defeated, concession |
| 7 | 😎 | Cool | Confident, in control |
| 8 | 😰 | Anxious | Under pressure, defensive |
| 9 | 🤨 | Skeptical | Doubting opponent's claim |

### Animation Effects

Each icon animates when the agent's turn begins:

| Animation | Duration | Description |
|-----------|----------|-------------|
| **Bounce** | 0.3s | Icon bounces on message send |
| **Pulse** | 0.5s | Icon pulses during typing |
| **Shake** | 0.3s | Icon shakes for angry/surprised |
| **Fade** | 0.2s | Smooth transition between states |

### State Transition Logic

```python
# src/gui/emotions.py

EMOTION_TRANSITIONS = {
    "happy": {
        "agreement": "happy",
        "contradiction": "angry",
        "question": "thinking",
    },
    "thinking": {
        "answer": "cool",
        "challenge": "skeptical",
        "defeat": "sad",
    },
    "angry": {
        "victory": "laughing",
        "defeat": "sad",
        "neutral": "thinking",
    },
    # ... etc
}
```

### Icon Display

```
┌─────────────────────┐
│   Agent: Samuel     │
│                     │
│   [😊 → 🤔]         │  ← Transition animation
│                     │
│   Status: Thinking  │
└─────────────────────┘
```

---

## 4-Way Split Layout

### With Moderator Panel

For advanced mode, a 4th panel shows the moderator perspective:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [MONITORING BAR]                                                    │
├────────────────┬────────────────┬────────────────┬─────────────────┤
│                │                │                │                 │
│   AGENT A      │   AGENT B      │   AGENT C      │   MODERATOR     │
│   😠           │   😂           │   🤔           │   🎯            │
│                │                │                │                 │
│   Flat Earth   │   Globe Earth  │   Skeptic      │   Fact-Checker  │
│   Advocate     │   Defender     │   Neutral      │   Arbiter       │
│                │                │                │                 │
│   [Chat...]    │   [Chat...]    │   [Chat...]    │   [Notes...]    │
│                │                │                │                 │
│                │                │                │   Score: A:2    │
│                │                │                │          B:3    │
│                │                │                │          C:1    │
├────────────────┴────────────────┴────────────────┴─────────────────┤
│ > _                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Moderator Functions

| Function | Description |
|----------|-------------|
| **Fact Check** | Verify claims against knowledge base |
| **Scoring** | Rate persuasiveness of arguments |
| **Steering** | Suggest topics or redirect debate |
| **Timer** | Control turn duration |
| **Intervention** | Break in with corrections |

---

## UI Components

### Terminal Styling

```css
/* Base terminal look */
.terminal {
    background-color: #1a1a2e;
    color: #16c79a;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 14px;
    line-height: 1.4;
}

/* Monitor bar */
.monitor-bar {
    background-color: #16213e;
    border-bottom: 1px solid #0f3460;
    padding: 4px 8px;
}

/* Chat panels */
.chat-panel {
    border: 1px solid #0f3460;
    margin: 4px;
    border-radius: 4px;
}

/* Agent icons */
.agent-icon {
    font-size: 32px;
    animation: bounce 0.3s ease;
}

/* Input area */
.input-area {
    background-color: #0f3460;
    border-top: 1px solid #16c79a;
    padding: 8px;
}
```

### Color Palette

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Blue | `#1a1a2e` |
| Primary Text | Mint | `#16c79a` |
| Secondary Text | Light Blue | `#4a9eff` |
| Border | Navy | `#0f3460` |
| Warning | Yellow | `#ffd369` |
| Error | Red | `#e94560` |
| Success | Green | `#16c79a` |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Chat text | JetBrains Mono | 14px | Normal |
| Agent names | JetBrains Mono | 16px | Bold |
| Monitor metrics | JetBrains Mono | 12px | Normal |
| Headers | JetBrains Mono | 18px | Bold |

---

## Animation Specifications

### Typing Indicator

```
Samuel is typing... ▓▓▓░░░░░░░░
                   ^^^^^^^ animated
```

### Message Appearance

```
1. Message container fades in (0.2s)
2. Text typewriter effect (varies by length)
3. Agent icon animates based on emotion
4. Scroll to bottom smoothly
```

### Turn Transitions

```
┌─────────────────────┐
│ Agent A speaking... │  ← Highlighted border
│ [😊 Animated]       │
└─────────────────────┘
        ↓ (transition)
┌─────────────────────┐
│ Agent B speaking... │  ← Highlighted border
│ [😠 Animated]       │
└─────────────────────┘
```

---

## User Interactions

### Input Methods

| Input | Action |
|-------|--------|
| Text + Enter | Send message (PersuChat mode) |
| Enter (empty) | Continue to next turn (3-Way mode) |
| `/mode persuachat` | Switch to 1-on-1 mode |
| `/mode firechat` | Switch to 3-way debate |
| `/monitor` | Toggle monitoring bar |
| `/help` | Show commands |
| `/quit` | Exit session |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+L` | Clear chat |
| `Ctrl+M` | Toggle monitoring |
| `Ctrl+S` | Save session |
| `Tab` | Auto-complete command |
| `↑/↓` | Scroll history |

---

## Session States

### State Diagram

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  PERSUCHAT  │◄───►│  FIRECHAT   │
│   (1-on-1)  │     │  (3-way)    │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               │
               ▼
        ┌─────────────┐
        │    END      │
        └─────────────┘
```

### Session Data

```python
# src/gui/session.py

@dataclass
class SessionState:
    mode: str  # "persuchat" | "firechat"
    turn: int
    agents: list[AgentState]
    history: list[Message]
    scores: dict[str, int]
    monitor_visible: bool
```

---

## Implementation Files

### Frontend Structure

```
src/gui/
├── __init__.py
├── app.py              # Main FastAPI app
├── websocket.py        # WebSocket handler
├── session.py          # Session state management
├── emotions.py         # Emotion state machine
├── templates/
│   └── index.html      # Main HTML template
└── static/
    ├── css/
    │   └── terminal.css
    └── js/
        ├── app.js      # Main application
        ├── monitor.js  # Monitoring bar
        ├── chat.js     # Chat panels
        └── animations.js
```

### Backend Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main UI |
| `/api/session` | POST | Create new session |
| `/api/session/{id}` | GET | Get session state |
| `/api/chat` | WebSocket | Real-time chat |
| `/api/monitor` | WebSocket | Real-time metrics |

---

## Accessibility

### Screen Reader Support

- All icons have aria-labels
- Status changes announced
- Keyboard navigation throughout

### Visual Accessibility

- High contrast mode available
- Text scaling supported
- Color-blind friendly indicators

---

## Related Files

- [plans/monitor.md](monitor.md) - Monitoring backend implementation
- [plans/models.md](models.md) - LLM models
- [plans/memory.md](memory.md) - OpenViking for knowledge retrieval
- [plans/docker.md](docker.md) - Container deployment
