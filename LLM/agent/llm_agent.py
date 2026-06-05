"""LLM-backed decision function with OpenAI and Anthropic support."""

from __future__ import annotations

import os
from typing import Literal

Provider = Literal["openai", "anthropic"]


def _detect_provider() -> Provider:
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in ("openai", "anthropic"):
        return explicit  # type: ignore[return-value]
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    raise RuntimeError(
        "No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env, "
        "or run with --mock for a scripted demo."
    )


def create_llm_agent(
    provider: Provider | None = None,
    model: str | None = None,
    temperature: float = 0.2,
):
    provider = provider or _detect_provider()

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        def decide(system_prompt: str, user_prompt: str) -> str:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""

        decide.provider = provider  # type: ignore[attr-defined]
        decide.model = model  # type: ignore[attr-defined]
        return decide

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = model or os.getenv("LLM_MODEL", "claude-3-5-haiku-latest")

        def decide(system_prompt: str, user_prompt: str) -> str:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            parts = [block.text for block in response.content if block.type == "text"]
            return "\n".join(parts)

        decide.provider = provider  # type: ignore[attr-defined]
        decide.model = model  # type: ignore[attr-defined]
        return decide

    raise ValueError(f"Unsupported provider: {provider}")
