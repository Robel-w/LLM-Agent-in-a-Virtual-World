#!/usr/bin/env python3
"""Run an LLM agent in a 2D escape-room world."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.llm_agent import create_llm_agent
from agent.mock_agent import create_mock_agent
from harness.loop import run_episode, save_log
from world import reset_world

console = Console()


def render_world_ascii(state) -> str:
    """Simple ASCII map for terminal display."""
    symbols = {
        "floor": ".",
        "wall": "#",
        "door": "D",
        "exit": "E",
    }
    ax, ay = state.agent.position
    lines = []
    for y in range(state.height):
        row = []
        for x in range(state.width):
            if (x, y) == (ax, ay):
                facing_glyph = {"north": "^", "east": ">", "south": "v", "west": "<"}[
                    state.agent.facing.value
                ]
                row.append(facing_glyph)
                continue
            entity = state.entity_at(x, y)
            if entity:
                if entity.kind == "item":
                    row.append("k")
                elif entity.kind == "door":
                    row.append("D" if entity.locked else "d")
                elif entity.kind == "readable":
                    row.append("?")
                else:
                    row.append("*")
                continue
            cell = state.cell_at(x, y)
            row.append(symbols.get(cell.value if cell else "floor", "?"))
        lines.append("".join(row))
    return "\n".join(lines)


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="LLM agent in a virtual grid world")
    parser.add_argument("--mock", action="store_true", help="Run scripted demo without an API key")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each observation and action")
    parser.add_argument("--log", type=str, default="", help="Save JSON run log to this path")
    parser.add_argument("--max-steps", type=int, default=40, help="Maximum steps before timeout")
    args = parser.parse_args()

    state = reset_world()
    state.max_steps = args.max_steps

    if args.mock:
        decide = create_mock_agent(state)
        mode = "mock (scripted)"
    else:
        decide = create_llm_agent()
        mode = f"{getattr(decide, 'provider', '?')} / {getattr(decide, 'model', '?')}"

    console.print(Panel.fit(f"[bold]Escape Room Agent[/bold]\nMode: {mode}\nGoal: {state.goal}"))
    console.print("[dim]Legend: ^>v< agent  k key  D locked door  d open door  E exit  ? note[/dim]")
    console.print(render_world_ascii(state))

    def on_step(record: dict) -> None:
        if args.verbose:
            return
        action = record.get("action") or {"parse_error": record.get("parse_error")}
        console.print(
            f"[cyan]Step {record['step']}[/cyan] "
            f"{action} -> {record['result'][:100]}"
        )
        console.print(render_world_ascii(state))
        console.print()

    log = run_episode(state, decide, verbose=args.verbose, on_step=on_step)

    table = Table(title="Episode Summary")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Success", str(log.success))
    table.add_row("Steps taken", str(len(log.steps)))
    table.add_row("Reason", log.termination_reason)
    console.print(table)

    if log.success:
        console.print("[green bold]Goal completed![/green bold]")
    else:
        console.print("[red bold]Goal not completed.[/red bold]")

    if args.log:
        save_log(log, args.log)
        console.print(f"Log saved to {args.log}")
    elif not args.verbose:
        default_log = Path("examples") / "last_run.json"
        default_log.parent.mkdir(exist_ok=True)
        save_log(log, str(default_log))
        console.print(f"Log saved to {default_log}")

    return 0 if log.success else 1


if __name__ == "__main__":
    sys.exit(main())
