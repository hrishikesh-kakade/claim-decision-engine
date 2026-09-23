"""Optional narration polish for key_findings.

The `statement` on every Finding is already a complete, evidence-grounded
sentence generated in plain Python by the Coverage & Exclusion Agent --
this module ONLY rephrases those sentences for readability when an LLM
is configured. It never introduces new facts: the prompt explicitly
forbids adding information not present in the input findings, and if the
LLM is unavailable (no API key) or its output can't be trusted to
preserve the facts, we fall back to the original deterministic statements
untouched. This keeps `key_findings` reproducible and evidence-grounded
even when an LLM is in the loop.

Output format is JSON (a list of strings), not free-text lines. Asking an
LLM to preserve an exact line count in plain prose is fragile -- it will
often add a preamble ("Here are the rephrased findings:"), a closing
remark, or wrap one sentence across two lines, none of which change the
*content* but all of which broke the old line-count check and caused a
safe-but-avoidable fallback. A JSON array is a format LLMs reliably
produce with the exact element count requested, so this is a strictly
easier target to hit -- without loosening what we require of the content.
"""
from __future__ import annotations

import json
import re

from ..llm import LLMClient
from ..models import Finding

_client: LLMClient | None = None


def _get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


SYSTEM = (
    "You rephrase insurance-claim findings into concise, plain-English sentences for a claims "
    "reviewer. Do not add any fact, number, or conclusion that is not already present in the input. "
    "Do not change any number. Respond with ONLY a JSON array of strings, no markdown code fence, "
    "no preamble, no commentary -- for example: [\"first rephrased sentence\", \"second rephrased sentence\"]. "
    "The array must have EXACTLY the same number of elements as the number of input findings, "
    "one rephrased sentence per finding, in the same order."
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def get_client() -> LLMClient:
    return _get_client()


def _parse_json_array(text: str) -> list[str] | None:
    # Strip a markdown code fence if the model added one despite instructions.
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"```$", "", stripped).strip()
    # Fall back to extracting the first [...] block if there's stray text
    # around it (a preamble the model added despite instructions).
    candidates = [stripped]
    m = _JSON_ARRAY_RE.search(stripped)
    if m:
        candidates.append(m.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
            return parsed
    return None


def narrate_findings(findings: list[Finding], status: str) -> tuple[list[str] | None, dict]:
    """Returns (rephrased_lines_or_None, llm_call_info). llm_call_info always
    reflects what actually happened (see LLMClient.last_call_info) so the
    caller can report, per request, whether the LLM was used."""
    client = _get_client()
    original = [f.statement for f in findings]
    if not client.available or not original:
        return None, {
            "provider": client.provider, "model": None, "called": False,
            "succeeded": False,
            "error": None if not original else "LLM_PROVIDER=none (or no API key configured) -- rule-engine-only mode.",
        }
    user = (
        f"Decision status: {status}\n\n"
        f"There are exactly {len(original)} findings. Return a JSON array of exactly {len(original)} strings.\n\n"
        "Findings:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(original))
    )
    text = client.complete(SYSTEM, user, max_tokens=800)
    info = dict(client.last_call_info)
    if not text:
        return None, info

    lines = _parse_json_array(text)
    if lines is None:
        info["succeeded"] = False
        info["error"] = (info.get("error") or "") + " [LLM output was not a valid JSON array; reverted to deterministic findings.]"
        return None, info
    if len(lines) != len(original):
        info["succeeded"] = False
        info["error"] = (
            (info.get("error") or "")
            + f" [LLM returned {len(lines)} items, expected {len(original)}; reverted to deterministic findings.]"
        )
        return None, info  # don't trust a reshaped/merged output; keep deterministic statements
    return lines, info
