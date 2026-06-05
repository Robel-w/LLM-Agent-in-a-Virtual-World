"""Agent-environment loop: observe → decide → act → feedback."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Protocol

from harness.actions import action_schema_prompt, parse_llm_response
from harness.observations import build_observation, observation_to_prompt
from world.environment import apply_action, is_terminal
from world.entities import StepResult, WorldState


class AgentDecisionFn(Protocol):
    def __call__(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass
class RunLog:
    goal: str
    steps: list[dict] = field(default_factory=list)
    success: bool = False
    termination_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "success": self.success,
            "termination_reason": self.termination_reason,
            "steps": self.steps,
        }


def run_episode(
    state: WorldState,
    decide: AgentDecisionFn,
    *,
    verbose: bool = False,
    on_step: Callable[[dict], None] | None = None,
) -> RunLog:
    system_prompt = action_schema_prompt()
    log = RunLog(goal=state.goal)

    while True:
        obs = build_observation(state)
        user_prompt = observation_to_prompt(obs)

        if verbose:
            print("\n--- OBSERVATION ---")
            print(user_prompt)

        raw_response = decide(system_prompt, user_prompt)
        action, error = parse_llm_response(raw_response)

        if error:
            # Give the model another chance next step via feedback
            state.last_feedback = f"Your last response was invalid: {error} Respond with valid JSON."
            step_record = {
                "step": state.step + 1,
                "observation": obs,
                "raw_response": raw_response,
                "parse_error": error,
                "result": state.last_feedback,
            }
            log.steps.append(step_record)
            if on_step:
                on_step(step_record)
            state.step += 1
            if state.step >= state.max_steps:
                log.termination_reason = "max_steps"
                break
            continue

        result = apply_action(state, action)
        step_record = {
            "step": state.step,
            "observation": obs,
            "thought": action.get("thought", ""),
            "action": {k: v for k, v in action.items() if k != "thought"},
            "raw_response": raw_response,
            "result": result.message,
            "success": result.success,
            "goal_complete": result.goal_complete,
        }
        log.steps.append(step_record)

        if verbose:
            print("\n--- AGENT ---")
            print(raw_response)
            print(f"\n--- RESULT ---\n{result.message}")

        if on_step:
            on_step(step_record)

        if is_terminal(state, result):
            log.success = result.goal_complete
            log.termination_reason = "goal_complete" if result.goal_complete else "max_steps"
            break

    return log


def save_log(log: RunLog, path: str) -> None:
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log.to_dict(), f, indent=2)
