"""Action schema, validation, and parsing."""

from __future__ import annotations

import json
import re
from typing import Any

VALID_ACTIONS = {"move", "turn", "pick_up", "use", "examine", "read", "wait"}


def action_schema_prompt() -> str:
    return """You control an agent in a 2D grid world. Each turn, respond with a single JSON object:

{
  "thought": "one or two sentences of reasoning",
  "action": "move" | "turn" | "pick_up" | "use" | "examine" | "read" | "wait",
  "direction": "left" | "right",        // required for turn
  "item_id": "golden_key",               // required for use
  "target_id": "exit_door"               // optional for use (defaults to entity in front)
}

Rules:
- move always steps forward relative to your facing direction.
- pick_up only works when standing on an item tile.
- use requires the item in inventory and a valid target in the cell ahead.
- Prefer purposeful actions; avoid repeating failed moves.
- Output JSON only, no markdown fences."""


def validate_action(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if "action" not in raw:
        return None, "Missing 'action' field."

    action = str(raw["action"]).strip().lower()
    if action not in VALID_ACTIONS:
        return None, f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    normalized: dict[str, Any] = {"action": action, "thought": raw.get("thought", "")}

    if action == "turn":
        direction = str(raw.get("direction", "")).strip().lower()
        if direction not in ("left", "right"):
            return None, "turn requires direction 'left' or 'right'."
        normalized["direction"] = direction

    if action == "use":
        item_id = raw.get("item_id")
        if not item_id:
            return None, "use requires item_id."
        normalized["item_id"] = str(item_id)
        if raw.get("target_id"):
            normalized["target_id"] = str(raw["target_id"])

    return normalized, None


def parse_llm_response(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Extract and validate JSON from model output."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()

    # Try to find a JSON object in the response
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None, "No JSON object found in model response."

    try:
        raw = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"

    if not isinstance(raw, dict):
        return None, "Expected a JSON object."

    return validate_action(raw)
