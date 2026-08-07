"""AI feature logic.

Every function returns a ``"source"`` field so the caller (and the frontend)
can tell honestly whether an answer came from a real model or from a fixed
template — the previous version of this module produced templated text
year-round and called it "AI" regardless of ``LLM_API_KEY``, which was never
wired to anything. With neither key set, these functions still work exactly
as before (deterministic, free, offline) and say so; with a key configured,
homework generation and lesson analysis call a real model and fall back to
the template on any error so a flaky/rate-limited API call never breaks the
request.

Two model backends are supported: Anthropic Claude (paid) and Google Gemini
(free tier at aistudio.google.com, no card required — the option for local/
test use). Anthropic wins if both keys happen to be set.
"""

from __future__ import annotations

import json
import logging

from ..core.config import get_settings

log = logging.getLogger("ai.engine")

_settings = get_settings()
_anthropic_client = None  # lazily constructed — the SDK opens no connection at import time
_gemini_model = None


def _has_model() -> bool:
    return bool(_settings.anthropic_api_key or _settings.gemini_api_key)


async def _complete(prompt: str) -> tuple[str, str] | None:
    """Call whichever provider is configured; returns (raw_text, source) or None."""
    if _settings.anthropic_api_key:
        global _anthropic_client
        if _anthropic_client is None:
            import anthropic

            _anthropic_client = anthropic.AsyncAnthropic(api_key=_settings.anthropic_api_key)
        response = await _anthropic_client.messages.create(
            model=_settings.anthropic_model,
            max_tokens=_settings.anthropic_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text, "anthropic"
    if _settings.gemini_api_key:
        global _gemini_model
        if _gemini_model is None:
            import google.generativeai as genai

            genai.configure(api_key=_settings.gemini_api_key)
            _gemini_model = genai.GenerativeModel(_settings.gemini_model)
        response = await _gemini_model.generate_content_async(prompt)
        return response.text, "gemini"
    return None


def _strip_json_fences(text: str) -> str:
    """Gemini (and occasionally Claude) wrap JSON in a ```json ... ``` block
    despite being asked for "nothing else" — strip that before parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _template_homework(subject: str, level: str, topic: str, num_tasks: int) -> dict:
    templates = [
        "Explain the concept of '{topic}' in your own words.",
        "Solve 5 practice problems about '{topic}' ({level} level).",
        "Find a real-world example where '{topic}' applies and describe it.",
        "Summarise the key rules of '{topic}' in a short paragraph.",
        "Prepare 3 questions about '{topic}' to discuss in the next lesson.",
    ]
    tasks = [templates[i % len(templates)].format(topic=topic, level=level) for i in range(num_tasks)]
    return {
        "subject": subject,
        "level": level,
        "topic": topic,
        "tasks": tasks,
        "estimated_minutes": num_tasks * 15,
        "source": "template",
    }


async def generate_homework(subject: str, level: str, topic: str, num_tasks: int) -> dict:
    if not _has_model():
        return _template_homework(subject, level, topic, num_tasks)
    prompt = (
        f"Create exactly {num_tasks} homework tasks for a {level}-level {subject} student "
        f"on the topic '{topic}'. Reply as a JSON array of {num_tasks} short task strings, "
        "nothing else."
    )
    try:
        raw, source = await _complete(prompt)  # type: ignore[misc]
        tasks = json.loads(_strip_json_fences(raw))
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("model did not return a task list")
        return {
            "subject": subject,
            "level": level,
            "topic": topic,
            "tasks": [str(t) for t in tasks[:num_tasks]],
            "estimated_minutes": num_tasks * 15,
            "source": source,
        }
    except Exception as exc:  # network error, bad JSON, rate limit, ...
        log.warning("Model homework generation failed, falling back to template: %s", exc)
        return _template_homework(subject, level, topic, num_tasks)


def _template_topic_explanation(subject: str, level: str, topic: str) -> dict:
    """No canned text can substitute for a real explanation of an arbitrary
    topic — unlike homework/lesson-analysis, there is no honest generic
    filler here. This says so plainly instead of faking a lesson."""
    content = (
        f"Подробное объяснение темы «{topic}» ({subject}, уровень {level}) требует "
        "подключённого AI — на сервере не настроен ни ANTHROPIC_API_KEY, ни "
        "GEMINI_API_KEY, поэтому эта функция сейчас не может дать содержательный "
        "ответ. Попробуйте позже или обратитесь к своему репетитору."
    )
    return {"subject": subject, "level": level, "topic": topic, "content": content, "source": "template"}


async def explain_topic(subject: str, level: str, topic: str) -> dict:
    if not _has_model():
        return _template_topic_explanation(subject, level, topic)
    prompt = (
        f"Explain the topic '{topic}' in {subject} to a {level}-level student, in Russian. "
        "Structure the answer with a short conceptual explanation, at least one concrete "
        "example (a code snippet in a ``` fenced block if the subject is programming-related, "
        "otherwise a worked example), and 2-3 common mistakes or tips. Use markdown: "
        "## headings, **bold** for key terms, and numbered/bulleted lists where useful. "
        "Reply with the explanation only, nothing else."
    )
    try:
        raw, source = await _complete(prompt)  # type: ignore[misc]
        return {"subject": subject, "level": level, "topic": topic, "content": raw.strip(), "source": source}
    except Exception as exc:
        log.warning("Model topic explanation failed, falling back to template: %s", exc)
        return _template_topic_explanation(subject, level, topic)


def _template_lesson_analysis(notes: str) -> dict:
    words = notes.split()
    sentences = [s.strip() for s in notes.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    key_points = sentences[:3]
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "key_points": key_points,
        "summary": " ".join(sentences[:2]) if sentences else "",
        "source": "template",
    }


async def analyze_lesson(notes: str) -> dict:
    if not _has_model() or not notes.strip():
        return _template_lesson_analysis(notes)
    prompt = (
        "Summarise these tutoring lesson notes for the student. Reply as JSON with keys "
        "\"summary\" (one sentence) and \"key_points\" (a list of up to 3 short strings). "
        f"Notes:\n{notes}"
    )
    try:
        raw, source = await _complete(prompt)  # type: ignore[misc]
        parsed = json.loads(_strip_json_fences(raw))
        return {
            "word_count": len(notes.split()),
            "sentence_count": notes.count(".") + notes.count("!") + notes.count("?"),
            "key_points": list(parsed.get("key_points", []))[:3],
            "summary": str(parsed.get("summary", "")),
            "source": source,
        }
    except Exception as exc:
        log.warning("Model lesson analysis failed, falling back to template: %s", exc)
        return _template_lesson_analysis(notes)


def analyze_progress(lessons_completed: int, hours_spent: int, avg_rating: float) -> dict:
    """Deterministic rule-based feedback — not model-backed, and not claimed to be."""
    if lessons_completed == 0:
        level = "just started"
    elif lessons_completed < 10:
        level = "beginner"
    elif lessons_completed < 30:
        level = "intermediate"
    else:
        level = "advanced"
    recommendation = (
        "Keep a steady weekly schedule to build momentum."
        if hours_spent < 20
        else "Great consistency — consider tackling more challenging material."
    )
    return {
        "level": level,
        "lessons_completed": lessons_completed,
        "hours_spent": hours_spent,
        "avg_rating": avg_rating,
        "recommendation": recommendation,
        "source": "rules",
    }


def recommend_tutors(candidates: list[dict], preferences: dict) -> list[dict]:
    """Rank candidate tutors against preferences — a scoring rule, not a model."""
    want_lang = preferences.get("language")
    want_category = preferences.get("category")
    max_price = preferences.get("max_price_cents")

    def score(t: dict) -> float:
        s = float(t.get("rating", 0)) * 2
        if want_lang and want_lang in (t.get("languages_taught") or []):
            s += 3
        if want_category and want_category in (t.get("specializations") or []):
            s += 3
        if max_price is not None and t.get("price_cents", 0) <= max_price:
            s += 1
        return s

    ranked = sorted(candidates, key=score, reverse=True)
    return [{"tutor_id": t.get("tutor_id"), "score": round(score(t), 2)} for t in ranked]
