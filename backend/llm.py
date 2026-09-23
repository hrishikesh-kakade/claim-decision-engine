"""
LLM client used only for natural-language synthesis (turning structured
findings into readable sentences) -- never for the numeric/date rules
themselves, which live in policy_rules.py / coverage_exclusion.py and are
computed in plain Python so they are exact and reproducible.

Provider is chosen from environment variables so the system runs on any
free/low-cost provider:
  LLM_PROVIDER=anthropic          -- needs ANTHROPIC_API_KEY
  LLM_PROVIDER=groq               -- needs GROQ_API_KEY (+ optional GROQ_MODEL)
  LLM_PROVIDER=openai_compatible  -- needs OPENAI_API_KEY (+ optional OPENAI_BASE_URL,
                                      works with Groq, Together, Ollama, etc. too)
  LLM_PROVIDER=none               -- deterministic template phrasing, no
                                      network call at all. This is the
                                      default fallback whenever no key is
                                      configured, which is what keeps the
                                      evaluation script reproducible for
                                      free with zero external calls.
  LLM_PROVIDER=auto (default)     -- picks the first of GROQ_API_KEY /
                                      ANTHROPIC_API_KEY / OPENAI_API_KEY that
                                      is set, else "none".

After every `complete()` call, `last_call_info` records exactly what
happened (provider, model, whether it actually returned text, and any
error) -- this is what main.py exposes via GET /llm-status and what the
orchestrator writes into the trace, so it's possible to *see*, per
request, whether the LLM was actually used or the deterministic fallback
kicked in.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("claim_engine.llm")


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "auto").lower()
        if self.provider == "auto":
            if os.getenv("GROQ_API_KEY"):
                self.provider = "groq"
            elif os.getenv("ANTHROPIC_API_KEY"):
                self.provider = "anthropic"
            elif os.getenv("OPENAI_API_KEY"):
                self.provider = "openai_compatible"
            else:
                self.provider = "none"

        self.last_call_info: dict = {
            "provider": self.provider,
            "model": None,
            "called": False,
            "succeeded": False,
            "error": None,
        }
        logger.info("LLMClient initialised with provider=%s", self.provider)

    @property
    def available(self) -> bool:
        return self.provider != "none"

    def complete(self, system: str, user: str, max_tokens: int = 600) -> Optional[str]:
        """Return plain text, or None on any failure/unavailability so
        callers always have a deterministic template fallback ready.
        Always updates self.last_call_info, even on failure/skip."""
        info = {"provider": self.provider, "model": None, "called": False, "succeeded": False, "error": None}

        if self.provider == "none":
            info["error"] = "LLM_PROVIDER=none (or no API key configured) -- rule-engine-only mode."
            self.last_call_info = info
            return None

        info["called"] = True
        try:
            if self.provider == "anthropic":
                import anthropic

                model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
                info["model"] = model
                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model=model, max_tokens=max_tokens, system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(b.text for b in resp.content if b.type == "text")

            elif self.provider == "groq":
                from groq import Groq

                model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
                info["model"] = model
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))

                # Reasoning models (e.g. openai/gpt-oss-20b, deepseek-r1-*)
                # spend tokens on a hidden "thinking" pass before writing the
                # visible answer, out of the same max_tokens budget -- so a
                # budget that's plenty for a non-reasoning model can leave
                # zero tokens for the actual output (finish_reason="length"
                # with empty content). Cap reasoning effort low for this
                # narration task (we only need a short rephrase, not deep
                # reasoning) and give a bigger token budget as a safety net.
                is_reasoning_model = any(tag in model.lower() for tag in ("gpt-oss", "deepseek-r1", "o1", "o3"))
                effective_max_tokens = max(max_tokens, 1536) if is_reasoning_model else max_tokens
                kwargs = dict(
                    model=model, max_tokens=effective_max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                if is_reasoning_model:
                    kwargs["reasoning_effort"] = os.getenv("GROQ_REASONING_EFFORT", "low")

                try:
                    resp = client.chat.completions.create(**kwargs)
                except Exception:
                    # Some models/SDK versions reject reasoning_effort -- retry
                    # once without it rather than failing the whole call.
                    kwargs.pop("reasoning_effort", None)
                    resp = client.chat.completions.create(**kwargs)

                choice = resp.choices[0]
                text = choice.message.content
                info["finish_reason"] = getattr(choice, "finish_reason", None)
                info["reasoning_effort_used"] = kwargs.get("reasoning_effort")

            elif self.provider == "openai_compatible":
                from openai import OpenAI

                model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                info["model"] = model
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    base_url=os.getenv("OPENAI_BASE_URL") or None,
                )
                resp = client.chat.completions.create(
                    model=model, max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                choice = resp.choices[0]
                text = choice.message.content
                info["finish_reason"] = getattr(choice, "finish_reason", None)
            else:
                info["error"] = f"Unknown LLM_PROVIDER={self.provider!r}"
                self.last_call_info = info
                logger.warning(info["error"])
                return None

            info["succeeded"] = bool(text)
            if not text:
                # No exception was raised, but the provider returned empty
                # content -- this used to surface as a bare "None" error with
                # no way to diagnose it. Now we capture *why*: usually the
                # response was truncated/refused/empty for a reason visible
                # in finish_reason (e.g. "length", "content_filter").
                info["error"] = (
                    f"Provider call succeeded but returned empty content "
                    f"(finish_reason={info.get('finish_reason')!r}). This can happen if "
                    f"max_tokens is too low for the model's reasoning/thinking tokens, "
                    f"or the model refused/filtered the request."
                )
                self.last_call_info = info
                logger.warning("LLM call returned empty content (provider=%s): %s", self.provider, info["error"])
                return None

            self.last_call_info = info
            logger.info("LLM call succeeded (provider=%s, model=%s)", self.provider, info["model"])
            return text

        except Exception as e:
            info["error"] = f"{type(e).__name__}: {e}"
            self.last_call_info = info
            logger.warning("LLM call failed (provider=%s): %s", self.provider, info["error"])
            return None
