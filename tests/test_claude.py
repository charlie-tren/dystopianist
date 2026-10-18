"""Claude is asked first, Gemini catches anything Claude cannot answer, and a
missing key says so on the run summary. Never calls the real API."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic  # noqa: E402
import httpx2  # noqa: E402

import claude  # noqa: E402
import gemini  # noqa: E402
import llm  # noqa: E402
import write as write_stage  # noqa: E402


def _msg(text='{"essay": "x"}', stop="end_turn"):
    return SimpleNamespace(
        stop_reason=stop,
        content=[SimpleNamespace(type="thinking", thinking=""),
                 SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1000, output_tokens=2000))


class Fake:
    def __init__(self):
        self.calls, self.reply, self.raises = [], _msg(), None
        self.messages = SimpleNamespace(create=self._create("plain"))
        self.beta = SimpleNamespace(
            messages=SimpleNamespace(create=self._create("beta")))

    def _create(self, path):
        def create(**kw):
            self.calls.append((path, kw))
            if self.raises:
                raise self.raises
            return self.reply
        return create


def _reset(key=True):
    fake = Fake()
    claude._client, claude._off = fake, None
    if key:
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    return fake


def main() -> int:
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(("  ok  " if ok else "  XX  ") + name)
        fails += 0 if ok else 1

    saved = os.environ.get("ANTHROPIC_API_KEY")
    real_gemini = gemini.generate
    gemini.generate = lambda *a, **k: '{"essay": "from gemini"}'
    try:
        fake = _reset()
        raw, by = llm.generate("p")
        check("claude answers first", by == "claude" and raw == '{"essay": "x"}')
        path, kw = fake.calls[0]
        check("essays are written on sonnet with the server-side fallback",
              path == "beta" and kw["model"] == "claude-sonnet-5-5"
              and kw["fallbacks"] == "default")
        check("no temperature is sent", "temperature" not in kw)

        fake = _reset()
        llm.generate("p", tier="judge")
        check("scoring runs on haiku",
              fake.calls[0][1]["model"] == "claude-haiku-5-5"
              and "fallbacks" not in fake.calls[0][1])

        fake = _reset(key=False)
        raw, by = llm.generate("p")
        check("no key falls back to gemini", by == "gemini" and fake.calls == [])
        check("and turns claude off for the run", bool(claude._off))

        fake = _reset()
        req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        fake.raises = anthropic.InternalServerError(
            "overloaded", response=httpx2.Response(529, request=req), body=None)
        raw, by = llm.generate("p")
        check("an outage falls back to gemini", by == "gemini")
        llm.generate("p")
        check("and claude is not asked again that run", len(fake.calls) == 1)

        fake = _reset()
        fake.reply = _msg(stop="refusal")
        raw, by = llm.generate("p")
        check("a refusal falls back for that call only",
              by == "gemini" and claude._off is None)

        check("the scorer is claude, so the archive drains onto its scale",
              write_stage.SCORER == "claude")
        check("gemini-written essays are not queued for a rewrite",
              "gemini" in write_stage.PRIMARY_WRITERS
              and "cloudflare" not in write_stage.PRIMARY_WRITERS)
    finally:
        gemini.generate = real_gemini
        claude._client, claude._off = None, None
        os.environ.pop("ANTHROPIC_API_KEY", None)
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved

    print("all claude checks pass" if not fails else f"{fails} FAILED")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
