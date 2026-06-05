"""Grid world simulation: entities, maps, and physics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"

    def left(self) -> Direction:
        order = [Direction.NORTH, Direction.WEST, Direction.SOUTH, Direction.EAST]
        return order[(order.index(self) + 1) % 4]

    def right(self) -> Direction:
        order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        return order[(order.index(self) + 1) % 4]

    def delta(self) -> tuple[int, int]:
        return {
            Direction.NORTH: (0, -1),
            Direction.EAST: (1, 0),
            Direction.SOUTH: (0, 1),
            Direction.WEST: (-1, 0),
        }[self]


class CellKind(str, Enum):
    FLOOR = "floor"
    WALL = "wall"
    DOOR = "door"
    EXIT = "exit"


@dataclass
class Item:
    id: str
    name: str
    description: str
    usable_on: Optional[str] = None  # entity id this item can interact with


@dataclass
class Entity:
    id: str
    kind: str
    name: str
    description: str
    position: tuple[int, int]
    blocking: bool = False
    locked: bool = False
    item: Optional[Item] = None


@dataclass
class AgentState:
    position: tuple[int, int]
    facing: Direction
    inventory: list[Item] = field(default_factory=list)


@dataclass
class StepResult:
    success: bool
    message: str
    goal_complete: bool = False


@dataclass
class WorldState:
    width: int
    height: int
    cells: list[list[CellKind]]
    entities: dict[str, Entity]
    agent: AgentState
    goal: str
    step: int = 0
    max_steps: int = 40
    last_feedback: str = "You awaken in a dim corridor. Find the key and reach the exit."

    def cell_at(self, x: int, y: int) -> Optional[CellKind]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return None

    def entity_at(self, x: int, y: int) -> Optional[Entity]:
        for entity in self.entities.values():
            if entity.position == (x, y):
                return entity
        return None

    def agent_forward_cell(self) -> tuple[int, int]:
        dx, dy = self.agent.facing.delta()
        x, y = self.agent.position
        return x + dx, y + dy


def build_escape_room() -> WorldState:
    """A small maze: find the golden key, unlock the door, reach the exit."""
    width, height = 10, 8
    cells = [[CellKind.FLOOR for _ in range(width)] for _ in range(height)]

    # Perimeter walls
    for x in range(width):
        cells[0][x] = CellKind.WALL
        cells[height - 1][x] = CellKind.WALL
    for y in range(height):
        cells[y][0] = CellKind.WALL
        cells[y][width - 1] = CellKind.WALL

    # Interior wall segment forcing a detour
    for y in range(1, 5):
        cells[y][4] = CellKind.WALL
    cells[4][4] = CellKind.FLOOR  # gap

    cells[3][7] = CellKind.DOOR
    cells[3][8] = CellKind.EXIT

    key_item = Item(
        id="golden_key",
        name="golden key",
        description="A small golden key that looks like it fits an old door.",
        usable_on="exit_door",
    )

    entities = {
        "golden_key": Entity(
            id="golden_key",
            kind="item",
            name="golden key",
            description="A glinting key on the floor.",
            position=(2, 5),
            blocking=False,
            item=key_item,
        ),
        "exit_door": Entity(
            id="exit_door",
            kind="door",
            name="locked door",
            description="A heavy wooden door blocking the exit corridor.",
            position=(7, 3),
            blocking=True,
            locked=True,
        ),
        "note": Entity(
            id="note",
            kind="readable",
            name="crumpled note",
            description="The ink is faded: 'The key hides where the corridor turns south.'",
            position=(2, 2),
            blocking=False,
        ),
    }

    agent = AgentState(position=(1, 3), facing=Direction.EAST)
    goal = "Find the golden key, unlock the exit door, and step onto the exit tile."

    return WorldState(
        width=width,
        height=height,
        cells=cells,
        entities=entities,
        agent=agent,
        goal=goal,
    )
