"""LLM access through the hackathon LiteLLM proxy, with a response cache and a hard budget.

Every call is an LLM span in neatlogs (via neatlogs.wrap) plus a CHAIN span carrying the
purpose, the cost reported by LiteLLM and whether the cache answered."""

import hashlib
import json
import os
import re
from pathlib import Path

import neatlogs
from openai import OpenAI

SMALL, MID, STRONG = "nova-lite", "claude-haiku", "claude-sonnet-4.6"


class BudgetExceeded(RuntimeError):
    pass


class LLM:
    def __init__(self, state_dir: Path, budget_usd: float = 1.0, no_cache: set[str] | None = None):
        self.client = neatlogs.wrap(OpenAI(
            api_key=os.environ["LITELLM_API_KEY"],
            base_url=os.environ.get("LITELLM_BASE_URL", "https://litellm.vision.aivar.app/v1"),
        ))
        self.cache_dir = state_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.budget_usd = budget_usd
        self.spent_usd = 0.0
        self.calls = 0
        self.cache_hits = 0
        self.no_cache = no_cache or set()   # purposes that must hit the model (for honest cost measurement)
        self.tokens_in = 0
        self.tokens_out = 0

    def complete(self, messages: list[dict], model: str = STRONG, purpose: str = "",
                 max_tokens: int = 2000, temperature: float = 0.0) -> str:
        key = hashlib.sha256(json.dumps([model, messages, max_tokens, temperature]).encode()).hexdigest()
        cached = self.cache_dir / f"{key}.json"
        with neatlogs.trace(f"llm.{purpose or 'call'}", kind="CHAIN",
                            **{"interlock.model": model, "interlock.purpose": purpose}) as span:
            if cached.exists() and purpose not in self.no_cache:
                self.cache_hits += 1
                span.set_attribute("interlock.cache_hit", True)
                return json.loads(cached.read_text(encoding="utf-8"))["text"]
            if self.spent_usd >= self.budget_usd:
                span.set_attribute("interlock.budget_exceeded", True)
                raise BudgetExceeded(f"run budget ${self.budget_usd:.2f} used up (${self.spent_usd:.4f})")
            raw = self.client.chat.completions.with_raw_response.create(
                model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
            resp = raw.parse()
            cost = float(raw.headers.get("x-litellm-response-cost") or 0.0)
            self.spent_usd += cost
            self.calls += 1
            if resp.usage:
                self.tokens_in += resp.usage.prompt_tokens or 0
                self.tokens_out += resp.usage.completion_tokens or 0
                span.set_attribute("interlock.tokens_in", resp.usage.prompt_tokens or 0)
            text = resp.choices[0].message.content or ""
            span.set_attribute("interlock.cache_hit", False)
            span.set_attribute("interlock.cost_usd", cost)
            span.set_attribute("interlock.run_spent_usd", round(self.spent_usd, 6))
            cached.write_text(json.dumps({"model": model, "text": text, "cost": cost}), encoding="utf-8")
            return text


def extract_code(text: str, lang: str = "python") -> str:
    """The first fenced code block, or the whole text if there is none."""
    m = re.search(rf"```(?:{lang})?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"
