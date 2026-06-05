"""Environment step logic: validate and apply agent actions."""

from __future__ import annotations

from world.entities import (
    AgentState,
    CellKind,
    Direction,
    StepResult,
    WorldState,
    build_escape_room,
)


def reset_world() -> WorldState:
    return build_escape_room()


def is_blocking(state: WorldState, x: int, y: int) -> bool:
    cell = state.cell_at(x, y)
    if cell in (CellKind.WALL, None):
        return True
    entity = state.entity_at(x, y)
    if entity and entity.blocking:
        return True
    return False


def _move_forward(state: WorldState) -> StepResult:
    fx, fy = state.agent_forward_cell()
    if is_blocking(state, fx, fy):
        entity = state.entity_at(fx, fy)
        if entity and entity.kind == "door" and entity.locked:
            return StepResult(False, f"You bump into the {entity.name}. It is locked.")
        return StepResult(False, "You cannot move there; something is blocking the way.")

    state.agent.position = (fx, fy)
    cell = state.cell_at(fx, fy)
    if cell == CellKind.EXIT:
        return StepResult(
            True,
            "You step through the exit. The mission is complete!",
            goal_complete=True,
        )
    return StepResult(True, f"You move forward to ({fx}, {fy}).")


def _turn(state: WorldState, direction: str) -> StepResult:
    if direction == "left":
        state.agent.facing = state.agent.facing.left()
    elif direction == "right":
        state.agent.facing = state.agent.facing.right()
    else:
        return StepResult(False, f"Unknown turn direction: {direction}")
    return StepResult(True, f"You turn {direction}; now facing {state.agent.facing.value}.")


def _pick_up(state: WorldState) -> StepResult:
    x, y = state.agent.position
    entity = state.entity_at(x, y)
    if not entity or entity.kind != "item" or not entity.item:
        return StepResult(False, "There is nothing here to pick up.")
    state.agent.inventory.append(entity.item)
    del state.entities[entity.id]
    return StepResult(True, f"You pick up the {entity.item.name}.")


def _use_item(state: WorldState, item_id: str, target_id: str | None) -> StepResult:
    item = next((i for i in state.agent.inventory if i.id == item_id), None)
    if not item:
        return StepResult(False, f"You are not carrying '{item_id}'.")

    fx, fy = state.agent_forward_cell()
    target = state.entity_at(fx, fy)
    if target_id:
        target = state.entities.get(target_id) or target

    if not target:
        return StepResult(False, "There is nothing in front of you to use that on.")

    if item.usable_on and item.usable_on != target.id:
        return StepResult(False, f"The {item.name} does not work on the {target.name}.")

    if target.kind == "door" and target.locked:
        target.locked = False
        target.blocking = False
        target.name = "open door"
        target.description = "The door hangs open."
        state.agent.inventory = [i for i in state.agent.inventory if i.id != item.id]
        return StepResult(True, f"You unlock the {target.name} with the {item.name}.")

    return StepResult(False, f"Using {item.name} on {target.name} has no effect.")


def _examine(state: WorldState) -> StepResult:
    x, y = state.agent.position
    entity = state.entity_at(x, y)
    if entity:
        return StepResult(True, f"You examine the {entity.name}: {entity.description}")
    cell = state.cell_at(x, y)
    return StepResult(True, f"You examine the {cell.value if cell else 'unknown'} tile here.")


def _read(state: WorldState) -> StepResult:
    x, y = state.agent.position
    entity = state.entity_at(x, y)
    if entity and entity.kind == "readable":
        return StepResult(True, f"You read the {entity.name}: {entity.description}")
    return StepResult(False, "There is nothing readable here.")


def apply_action(state: WorldState, action: dict) -> StepResult:
    """Apply a validated action dict and mutate world state."""
    name = action["action"]
    state.step += 1

    if name == "move":
        result = _move_forward(state)
    elif name == "turn":
        result = _turn(state, action.get("direction", "left"))
    elif name == "pick_up":
        result = _pick_up(state)
    elif name == "use":
        result = _use_item(state, action.get("item_id", ""), action.get("target_id"))
    elif name == "examine":
        result = _examine(state)
    elif name == "read":
        result = _read(state)
    elif name == "wait":
        result = StepResult(True, "You wait and observe your surroundings.")
    else:
        result = StepResult(False, f"Unknown action: {name}")

    state.last_feedback = result.message
    return result


def is_terminal(state: WorldState, last_result: StepResult) -> bool:
    if last_result.goal_complete:
        return True
    if state.step >= state.max_steps:
        return True
    return False
