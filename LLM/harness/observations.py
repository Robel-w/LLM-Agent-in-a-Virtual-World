"""Structured observation format for the LLM agent."""

from __future__ import annotations

from world.entities import CellKind, Direction, WorldState


DIRECTION_NAMES = {
    Direction.NORTH: "north",
    Direction.EAST: "east",
    Direction.SOUTH: "south",
    Direction.WEST: "west",
}


def _describe_cell(state: WorldState, x: int, y: int) -> dict:
    cell = state.cell_at(x, y)
    entity = state.entity_at(x, y)
    info: dict = {"x": x, "y": y}
    if cell is None:
        info["kind"] = "void"
    else:
        info["kind"] = cell.value
    if entity:
        info["entity"] = {
            "id": entity.id,
            "name": entity.name,
            "kind": entity.kind,
            "locked": entity.locked if entity.kind == "door" else None,
        }
    return info


def _visible_cells(state: WorldState) -> list[dict]:
    """Return cells in front and to the sides (limited egocentric view)."""
    x, y = state.agent.position
    facing = state.agent.facing
    dx, dy = facing.delta()

    cells = [_describe_cell(state, x, y)]

    # Cell directly ahead
    cells.append(_describe_cell(state, x + dx, y + dy))

    # Side cells (perpendicular to facing)
    if facing in (Direction.NORTH, Direction.SOUTH):
        cells.append(_describe_cell(state, x - 1, y))
        cells.append(_describe_cell(state, x + 1, y))
    else:
        cells.append(_describe_cell(state, x, y - 1))
        cells.append(_describe_cell(state, x, y + 1))

    return cells


def build_observation(state: WorldState) -> dict:
    """Machine-readable observation the harness sends to the LLM."""
    inventory = [
        {"id": item.id, "name": item.name, "description": item.description}
        for item in state.agent.inventory
    ]

    nearby_entities = []
    ax, ay = state.agent.position
    for entity in state.entities.values():
        ex, ey = entity.position
        if abs(ex - ax) + abs(ey - ay) <= 3:
            nearby_entities.append(
                {
                    "id": entity.id,
                    "name": entity.name,
                    "kind": entity.kind,
                    "position": {"x": ex, "y": ey},
                    "distance": abs(ex - ax) + abs(ey - ay),
                    "locked": entity.locked if entity.kind == "door" else None,
                }
            )

    return {
        "step": state.step,
        "max_steps": state.max_steps,
        "goal": state.goal,
        "agent": {
            "position": {"x": state.agent.position[0], "y": state.agent.position[1]},
            "facing": state.agent.facing.value,
            "inventory": inventory,
        },
        "egocentric_view": _visible_cells(state),
        "nearby_entities": sorted(nearby_entities, key=lambda e: e["distance"]),
        "last_feedback": state.last_feedback,
        "available_actions": [
            {"action": "move", "description": "Step forward one tile in the direction you face"},
            {"action": "turn", "direction": "left|right", "description": "Rotate in place"},
            {"action": "pick_up", "description": "Pick up an item on your current tile"},
            {"action": "use", "item_id": "...", "target_id": "optional", "description": "Use a carried item on what is in front of you"},
            {"action": "examine", "description": "Look closely at your current tile"},
            {"action": "read", "description": "Read text on your current tile"},
            {"action": "wait", "description": "Pause and reconsider"},
        ],
    }


def observation_to_prompt(obs: dict) -> str:
    """Render observation as compact natural language for the LLM."""
    agent = obs["agent"]
    lines = [
        f"GOAL: {obs['goal']}",
        f"STEP: {obs['step']} / {obs['max_steps']}",
        "",
        f"Position: ({agent['position']['x']}, {agent['position']['y']})  Facing: {agent['facing']}",
    ]

    if agent["inventory"]:
        items = ", ".join(i["name"] for i in agent["inventory"])
        lines.append(f"Inventory: {items}")
    else:
        lines.append("Inventory: (empty)")

    lines.append("")
    lines.append("What you see nearby:")
    for cell in obs["egocentric_view"]:
        label = f"  ({cell['x']},{cell['y']}) {cell['kind']}"
        if "entity" in cell:
            ent = cell["entity"]
            extra = " [LOCKED]" if ent.get("locked") else ""
            label += f" — {ent['name']}{extra}"
        lines.append(label)

    if obs["nearby_entities"]:
        lines.append("")
        lines.append("Known objects in range:")
        for ent in obs["nearby_entities"]:
            lock = " (locked)" if ent.get("locked") else ""
            lines.append(
                f"  - {ent['name']} [{ent['kind']}] at ({ent['position']['x']},{ent['position']['y']}), "
                f"distance {ent['distance']}{lock}"
            )

    lines.append("")
    lines.append(f"Last result: {obs['last_feedback']}")
    lines.append("")
    lines.append("Respond with JSON only:")
    lines.append('{"thought": "brief reasoning", "action": "<name>", ...optional fields}')
    return "\n".join(lines)
