"""
Free / optional LLM providers for Silent Stakeholder.

Priority (first that works):
  1. GROQ_API_KEY          — free tier at console.groq.com (recommended)
  2. GEMINI_API_KEY        — free tier at aistudio.google.com
  3. OPENROUTER_API_KEY    — optional; many free models
  4. Ollama local          — if `ollama` is running on :11434
  5. ANTHROPIC_API_KEY     — paid, only if you already have it
  6. None                  — callers should fall back to heuristics

No credit card required for Groq or Gemini free tiers.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_dotenv() -> None:
    """Tiny .env loader so GROQ_API_KEY / GEMINI_API_KEY work without python-dotenv."""
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        # .env wins for local hackathon setup (override empty/stale shell exports)
        if key and val:
            os.environ[key] = val


_load_dotenv()


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str


def _env(*names: str) -> Optional[str]:
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return None


def active_provider() -> dict:
    """Describe which backend will be used (for UI / debugging)."""
    if _env("OPENAI_API_KEY"):
        return {
            "id": "openai",
            "label": "OpenAI",
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        }
    if _env("GROQ_API_KEY"):
        return {
            "id": "groq",
            "label": "Groq (free)",
            "model": os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
        }
    if _env("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        return {
            "id": "gemini",
            "label": "Google Gemini (free)",
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        }
    if _env("OPENROUTER_API_KEY"):
        return {
            "id": "openrouter",
            "label": "OpenRouter",
            "model": os.environ.get(
                "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"
            ),
        }
    if _ollama_alive():
        return {
            "id": "ollama",
            "label": "Ollama (local)",
            "model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
        }
    if _env("ANTHROPIC_API_KEY"):
        return {
            "id": "anthropic",
            "label": "Anthropic Claude",
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        }
    return {
        "id": "heuristic",
        "label": "Offline heuristics (no API key)",
        "model": "pattern-packs",
    }


def available() -> bool:
    return active_provider()["id"] != "heuristic"


def _ollama_alive() -> bool:
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/tags", method="GET"
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _redact(text: str) -> str:
    """Avoid leaking API keys from URLs/error bodies into logs."""
    return re.sub(r"(key=)[^&\s]+", r"\1***", text, flags=re.I)


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        safe_url = _redact(url.split("?", 1)[0])
        raise RuntimeError(f"HTTP {e.code} from {safe_url}: {_redact(body)[:400]}") from e


def _openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    provider: str,
) -> LLMResponse:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    out = _post_json(
        f"{base_url.rstrip('/')}/chat/completions",
        payload,
        {"Authorization": f"Bearer {api_key}"},
    )
    text = out["choices"][0]["message"]["content"]
    return LLMResponse(text=text.strip(), provider=provider, model=model)


def _gemini(system: str, user: str, max_tokens: int) -> LLMResponse:
    key = _env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    # flash-latest / thinking models can burn the output budget on internal
    # reasoning and truncate mid-sentence. Request a large budget and disable
    # thinking when the API supports it.
    out_tokens = max(int(max_tokens), 2048)
    gen_cfg: dict = {
        "temperature": 0.2,
        "maxOutputTokens": out_tokens,
        "thinkingConfig": {"thinkingBudget": 0},
    }
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen_cfg,
    }
    try:
        out = _post_json(url, payload, {})
    except RuntimeError as e:
        # Older models reject thinkingConfig — retry without it.
        if "thinking" in str(e).lower() or "400" in str(e):
            gen_cfg.pop("thinkingConfig", None)
            payload["generationConfig"] = gen_cfg
            out = _post_json(url, payload, {})
        else:
            raise
    candidates = out.get("candidates") or []
    if not candidates:
        feedback = out.get("promptFeedback") or out.get("error") or out
        raise RuntimeError(f"Gemini returned no candidates: {_redact(str(feedback))[:300]}")
    cand0 = candidates[0]
    content = cand0.get("content") or {}
    parts = content.get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    if not text:
        raise RuntimeError(
            f"Gemini empty text (finish={cand0.get('finishReason')}, "
            f"keys={list(content.keys())})"
        )
    # Surface truncation so callers can fall back to a complete answer.
    finish = (cand0.get("finishReason") or "").upper()
    if finish in {"MAX_TOKENS", "LENGTH"}:
        text += "\n\n_(response truncated by model token limit)_"
    return LLMResponse(text=text, provider="gemini", model=model)


def _ollama(system: str, user: str, max_tokens: int) -> LLMResponse:
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    out = _post_json("http://127.0.0.1:11434/api/chat", payload, {}, timeout=120)
    return LLMResponse(
        text=(out.get("message") or {}).get("content", "").strip(),
        provider="ollama",
        model=model,
    )


def _anthropic(system: str, user: str, max_tokens: int) -> LLMResponse:
    import anthropic

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return LLMResponse(
        text=resp.content[0].text.strip(), provider="anthropic", model=model
    )


def complete(
    prompt: str,
    *,
    system: str = "You are a careful product analyst. Be concise and grounded.",
    max_tokens: int = 500,
) -> LLMResponse:
    """Call the first available free/paid LLM. Raises if only heuristics remain."""
    info = active_provider()
    pid = info["id"]

    if pid == "openai":
        return _openai_compatible(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=_env("OPENAI_API_KEY"),
            model=info["model"],
            system=system,
            user=prompt,
            max_tokens=max_tokens,
            provider="openai",
        )
    if pid == "groq":
        return _openai_compatible(
            base_url="https://api.groq.com/openai/v1",
            api_key=_env("GROQ_API_KEY"),
            model=info["model"],
            system=system,
            user=prompt,
            max_tokens=max_tokens,
            provider="groq",
        )
    if pid == "gemini":
        return _gemini(system, prompt, max_tokens)
    if pid == "openrouter":
        return _openai_compatible(
            base_url="https://openrouter.ai/api/v1",
            api_key=_env("OPENROUTER_API_KEY"),
            model=info["model"],
            system=system,
            user=prompt,
            max_tokens=max_tokens,
            provider="openrouter",
        )
    if pid == "ollama":
        return _ollama(system, prompt, max_tokens)
    if pid == "anthropic":
        return _anthropic(system, prompt, max_tokens)

    raise RuntimeError(
        "No LLM configured. Set OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, "
        "or install Ollama."
    )


def parse_json_object(text: str) -> dict:
    """Extract a JSON object from model output (handles markdown fences)."""
    raw = text.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise
        return json.loads(m.group(0))
