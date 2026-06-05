"""Deterministic scripted agent for offline demos without an API key."""

from __future__ import annotations

import json
from collections import deque

from world.entities import Direction, WorldState
from world.environment import is_blocking


def _json_action(thought: str, **fields) -> str:
    payload = {"thought": thought, **fields}
    return json.dumps(payload)


def _bfs_path(state: WorldState, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    if start == goal:
        return [start]

    queue: deque[tuple[int, int]] = deque([start])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}

    while queue:
        x, y = queue.popleft()
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in parent:
                continue
            if is_blocking(state, nx, ny) and (nx, ny) != goal:
                continue
            parent[(nx, ny)] = (x, y)
            if (nx, ny) == goal:
                path = [(nx, ny)]
                cur = (x, y)
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                return list(reversed(path))
            queue.append((nx, ny))

    return []


def create_mock_agent(state: WorldState):
    """Plan with BFS: key -> door approach tile -> unlock -> exit."""
    plan: list[dict] = []
    facing = state.agent.facing

    def turn_to(target: Direction) -> None:
        nonlocal facing
        order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        while facing != target:
            ci, ti = order.index(facing), order.index(target)
            diff = (ti - ci) % 4
            if diff == 1:
                plan.append({"action": "turn", "direction": "right"})
                facing = order[(ci + 1) % 4]
            elif diff == 3:
                plan.append({"action": "turn", "direction": "left"})
                facing = order[(ci - 1) % 4]
            else:
                plan.append({"action": "turn", "direction": "right"})
                facing = order[(ci + 1) % 4]

    def follow_path(path: list[tuple[int, int]]) -> None:
        x, y = path[0]
        for nx, ny in path[1:]:
            if nx > x:
                turn_to(Direction.EAST)
            elif nx < x:
                turn_to(Direction.WEST)
            elif ny > y:
                turn_to(Direction.SOUTH)
            elif ny < y:
                turn_to(Direction.NORTH)
            plan.append({"action": "move"})
            x, y = nx, ny

    start = state.agent.position
    key_pos = (2, 5)
    door_approach = (6, 3)

    follow_path(_bfs_path(state, start, key_pos))
    plan.append({"action": "pick_up"})
    follow_path(_bfs_path(state, key_pos, door_approach))

    turn_to(Direction.EAST)
    plan.append({"action": "use", "item_id": "golden_key", "target_id": "exit_door"})
    plan.append({"action": "move"})
    plan.append({"action": "move"})

    index = 0

    def decide(system_prompt: str, user_prompt: str) -> str:
        nonlocal index
        if index >= len(plan):
            return _json_action("Goal should be complete; waiting.", action="wait")

        step = plan[index]
        index += 1
        thought = f"Executing planned step {index}/{len(plan)} toward the exit."
        return _json_action(thought, **step)

    decide.provider = "mock"  # type: ignore[attr-defined]
    decide.model = "scripted-planner"  # type: ignore[attr-defined]
    return decide
