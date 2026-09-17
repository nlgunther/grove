"""
text_to_ics/llm_extractor.py

LLM-backed extractor: handles the free text HeuristicExtractor can't
(multiple events buried in a paragraph, vague relative phrasing, no
per-line structure required). Optional — the `anthropic` package is
only imported here, so installing/using text_to_ics with the
heuristic backend never requires it.

Enable with: pip install "grove[text2ics]" (or `uv add --optional
text2ics anthropic` at the repo root), and set ANTHROPIC_API_KEY.
"""
import json
from datetime import datetime

from .models import EventSpec

_SYSTEM_PROMPT = """\
Extract calendar events from the user's text. Return ONLY a JSON array,
no prose, matching this shape for each event:

{"title": str, "start": "<ISO 8601 datetime, tz-aware>",
 "end": "<ISO 8601 datetime or null>", "all_day": bool,
 "location": str or null, "description": str or null}

Resolve relative dates/times ("tomorrow", "next Tuesday", "in an hour")
against the reference datetime given below. If a line or phrase has no
resolvable date, omit it rather than guessing.

Reference datetime (tz-aware, use its timezone for resolved times):
{reference}
"""


class LLMExtractor:
    """Extracts EventSpecs from arbitrary free text via an LLM call."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.model = model

    def extract(self, text: str, *, reference: datetime) -> list[EventSpec]:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "LLMExtractor requires the 'anthropic' package. "
                "Install with: pip install \"grove[text2ics]\""
            ) from exc

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT.format(reference=reference.isoformat()),
            messages=[{"role": "user", "content": text}],
        )
        payload = json.loads(response.content[0].text)
        return [self._to_spec(item) for item in payload]

    @staticmethod
    def _to_spec(item: dict) -> EventSpec:
        return EventSpec(
            title=item["title"],
            start=datetime.fromisoformat(item["start"]),
            end=datetime.fromisoformat(item["end"]) if item.get("end") else None,
            all_day=item.get("all_day", False),
            location=item.get("location"),
            description=item.get("description"),
        )
