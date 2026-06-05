# LLM Agent in a Virtual World

An intern-challenge project: a small **agent harness** that connects a language model to a 2D grid world. The agent perceives structured state, chooses validated actions, and completes a goal-directed escape-room task.

## Quick start

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Run without an API key (scripted demo)

```bash
python main.py --mock
```

This runs a deterministic planner through the same harness interface an LLM uses, so you can verify the world and loop without credentials.

### 3. Run with an LLM

Copy `.env.example` to `.env` and set one API key:

```bash
copy .env.example .env
```

```env
OPENAI_API_KEY=sk-...
# or ANTHROPIC_API_KEY=sk-ant-...
```

Then:

```bash
python main.py
python main.py -v              # verbose: print full observations + model output
python main.py --log run.json  # save structured JSON log
```

Optional env vars: `LLM_PROVIDER` (`openai` | `anthropic`), `LLM_MODEL`.

## The task

**Goal:** Find the golden key, unlock the exit door, and step onto the exit tile.

The world is a 10×8 grid with walls, a readable note, a key, a locked door, and an exit. The agent starts in a corridor facing east.

## Example output

```
Escape Room Agent
Mode: mock (scripted)
Goal: Find the golden key, unlock the exit door, and step onto the exit tile.

Legend: ^>v< agent  k key  D locked door  d open door  E exit  ? note
##########
#>...#...#
#....#...#
#....D.E.#
##########

Step 1 {'action': 'turn', 'direction': 'right'} → You turn right; now facing south.
...
Step N {'action': 'move'} → You step through the exit. The mission is complete!

Goal completed!
```

A full recorded run is in [`examples/sample_run.json`](examples/sample_run.json).

## Architecture

```
main.py          CLI entry point
world/           Grid simulation (entities, physics, task map)
harness/         Agent–environment interface
  observations   Structured state → LLM prompt
  actions        JSON schema, parsing, validation
  loop           observe → decide → act → feedback
agent/           Decision backends (OpenAI, Anthropic, mock)
```

### Observation format

Each step the harness builds a JSON observation with:

- **Goal and step budget** — so the model knows success criteria and urgency
- **Egocentric view** — current tile, tile ahead, and side tiles (not full omniscient map)
- **Nearby entities** — objects within Manhattan distance 3
- **Inventory** — carried items with IDs usable in `use` actions
- **Last feedback** — result of the previous action (critical for closed-loop control)

The LLM receives a compact natural-language rendering plus the action schema.

### Action space

| Action | Description |
|--------|-------------|
| `move` | Step forward relative to facing |
| `turn` | Rotate left or right |
| `pick_up` | Take item on current tile |
| `use` | Apply inventory item to entity ahead (e.g. key on door) |
| `examine` | Inspect current tile |
| `read` | Read text on current tile |
| `wait` | No-op |

The model must respond with JSON:

```json
{"thought": "...", "action": "move"}
```

Invalid responses are rejected; the harness feeds the parse error back as environment feedback on the next turn.

## Design choices

**Why a 2D grid?** It keeps the world simple while making the harness the focus: observation design, action validation, and the feedback loop matter more than rendering.

**Why egocentric partial views?** Full map observations make the task trivial and don't test reasoning under uncertainty. Limited visibility forces the agent to explore, remember prior feedback, and plan.

**Why structured JSON actions?** Free-text commands are brittle to parse. A fixed schema with server-side validation ensures actions are executable and gives clear error messages when the model hallucinates invalid moves.

**What worked:** Separating `world/` (simulation) from `harness/` (LLM interface) makes it easy to swap worlds or agents. Feeding `last_feedback` every step significantly improves LLM recovery from blocked moves.

**What didn't:** Models occasionally wrap JSON in markdown despite instructions; the parser strips fences as a fallback. Very small step budgets cause timeouts before the agent explores enough.

## Project layout

```
.
├── main.py
├── requirements.txt
├── world/
├── harness/
├── agent/
└── examples/
    └── sample_run.json
```


