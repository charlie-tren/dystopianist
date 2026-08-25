"""Where the text comes from. Two free providers, tried in order.

Gemini's free tier is generous per minute and stingy per DAY - one bad gate that
retries three times can spend the day's quota, which is exactly what happened on
25/08/2026 and left the site empty. So the generator no longer depends on a single
free tier: if Gemini refuses, Cloudflare Workers AI takes the run.

Both are free and neither needs a card. Cloudflare's credentials are already on this
machine for The Aftertimes' illustrations, so it costs nothing new to reach.

    GEMINI_API_KEY                 Google AI Studio, free tier
    CF_ACCOUNT_ID, CF_API_TOKEN    Cloudflare Workers AI, free neurons/day
"""
from __future__ import annotations

import json
import os
import re

import requests

import gemini

CF_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CF_TIMEOUT = 120


class NoProvider(RuntimeError):
    pass


def _cloudflare(prompt: str, temperature: float) -> str:
    acct, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (acct and tok):
        raise NoProvider("CF_ACCOUNT_ID / CF_API_TOKEN not set")
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{CF_MODEL}",
        headers={"Authorization": f"Bearer {tok}"},
        json={"messages": [{"role": "user", "content": prompt}],
              "temperature": temperature, "max_tokens": 900},
        timeout=CF_TIMEOUT)
    if r.status_code != 200:
        raise NoProvider(f"cloudflare HTTP {r.status_code}: {r.text[:160]}")
    d = r.json()
    if not d.get("success"):
        raise NoProvider(f"cloudflare: {str(d.get('errors'))[:160]}")
    # Workers AI answers with an OpenAI-shaped payload, and when the model emits
    # JSON the API hands it back ALREADY PARSED as a dict rather than as text.
    # Gemini always returns a string, so normalise here and let the caller stay simple.
    res = d["result"]
    out = res.get("response")
    if out is None and res.get("choices"):
        out = res["choices"][0].get("message", {}).get("content")
    return out


def generate(prompt: str, temperature: float = 0.95, prefer: str | None = None) -> tuple[str, str]:
    """Returns (raw text, which provider produced it). The caller records the
    provider on the essay, so a batch that reads differently can be traced to the
    model that wrote it rather than guessed at."""
    order = ["gemini", "cloudflare"]
    if prefer:
        order = [prefer] + [p for p in order if p != prefer]
    problems = []
    for name in order:
        try:
            if name == "gemini":
                return gemini.generate(prompt, temperature=temperature), "gemini"
            return _cloudflare(prompt, temperature), "cloudflare"
        except Exception as exc:                     # noqa: BLE001
            problems.append(f"{name}: {type(exc).__name__} {str(exc)[:110]}")
    raise NoProvider(" | ".join(problems))


def extract_json(raw):
    """Gemini is asked for JSON and obeys. The open models often wrap it in prose or
    fences, so fall back to the first {...} span, and then to treating the whole
    reply as the essay - which is what they do when they ignore the format entirely."""
    if isinstance(raw, dict):        # already parsed - see _cloudflare
        return raw
    try:
        return gemini.extract_json(raw)
    except Exception:
        m = re.search(r'"essay"\s*:\s*"(.*?)"\s*[},]', raw, re.S)
        if m:
            return {"essay": json.loads('"' + m.group(1) + '"')}
        body = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        body = re.sub(r'^\s*\{?\s*"?essay"?\s*:?\s*"?', "", body).strip().rstrip('"}').strip()
        if len(body.split()) > 60:
            return {"essay": body}
        raise
