"""AI sentiment engine.

Primary path: OpenAI GPT-4o-mini via the Responses API.
Fallback path: a lightweight rule-based lexicon classifier so the
platform keeps working without an API key (important for demos/portfolio).

Two layers, both used by the scheduler:
  1. classify_review(text)        → label + confidence
  2. summarize_product(...)       → one-line AI summary + top keywords
"""

import asyncio
import logging
import re
from typing import List, Tuple

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_POSITIVE_WORDS = {
    "amazing", "awesome", "best", "excellent", "great", "love", "loved",
    "perfect", "fast", "quick", "value", "worth", "good", "nice", "smooth",
    "camera", "battery", "battery life", "fluid", "gorgeous", "premium",
    "outstanding", "fantastic", "superb", "recommend", "happy", "impressive",
    "sharp", "crisp", "responsive", "efficient", "sturdy", "solid",
}
_NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "worst", "poor", "slow", "delay", "delayed",
    "overheating", "heats", "heating", "broken", "defect", "defective",
    "refund", "return", "useless", "waste", "disappoint", "disappointed",
    "lag", "lags", "freeze", "crashes", "cheap", "flimsy", "cracked",
    "scam", "fake", "worried", "regret", "annoying", "problem", "issue",
    "complaint", "dead", "smelly", "noise", "noisy", "blocked", "failed",
}
_NEUTRAL_WORDS = {
    "okay", "ok", "average", "decent", "fine", "expected", "standard",
    "usual", "typical", "basic", "normal", "alright", "mediocre",
}

_SENTIMENT_MODEL_PROMPT = """You are an e-commerce sentiment analyst for the Indian market.
Classify the customer review below.

Return JSON exactly like:
{"label": "positive"|"negative"|"neutral", "score": 0.0-1.0, "reason": "short"}

Rules:
- score is CONFIDENCE in the label, not intensity (0.0-1.0).
- Watch for Hinglish (Hindi+English mix) and Indian-English phrasing.
- "battery backup is op" → positive. "delivery late in Tier-2" → negative but note product vs logistics.

Review: {text}"""


# ─── Rule-based fallback ────────────────────────────────────────────────
def _fallback_classify(text: str) -> Tuple[str, float]:
    lowered = text.lower()
    score = 0.0
    hits = 0
    for word in _POSITIVE_WORDS:
        if word in lowered:
            score += 1.0
            hits += 1
    for word in _NEGATIVE_WORDS:
        if word in lowered:
            score -= 1.0
            hits += 1
    for word in _NEUTRAL_WORDS:
        if word in lowered:
            hits += 1

    if hits == 0:
        return "neutral", 0.5

    ratio = score / (hits + 1e-6)
    label = "positive" if ratio > 0.15 else "negative" if ratio < -0.15 else "neutral"
    confidence = min(0.95, 0.5 + abs(ratio) * 0.5)
    return label, round(confidence, 3)


# ─── OpenAI path ────────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def _llm_classify(client: AsyncOpenAI, text: str) -> Tuple[str, float]:
    response = await client.responses.create(
        model=settings.openai_model,
        instructions=_SENTIMENT_MODEL_PROMPT,
        input=text,
        temperature=0.2,
    )
    raw = response.output_text.strip()
    import json

    parsed = json.loads(raw)
    label = str(parsed.get("label", "neutral")).lower()
    if label not in {"positive", "negative", "neutral"}:
        label = "neutral"
    confidence = max(0.0, min(1.0, float(parsed.get("score", 0.6))))
    return label, round(confidence, 3)


def _needs_ai(text: str) -> bool:
    return len(text.strip()) >= settings.ai_min_review_length


async def classify_review(text: str) -> Tuple[str, float]:
    """Classify a review, using OpenAI when configured, else fallback."""
    text = (text or "").strip()
    if not text:
        return "neutral", 0.0

    if settings.openai_api_key and _needs_ai(text):
        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            return await _llm_classify(client, text)
        except Exception as exc:  # pragma: no cover - network flake
            logger.warning("OpenAI sentiment failed, using fallback: %s", exc)
            return _fallback_classify(text)

    return _fallback_classify(text)


_SUMMARY_PROMPT = """You are a senior market-intelligence analyst for Indian e-commerce.
You are given the latest customer reviews for one product on Flipkart/Amazon.in.

Write a ONE-LINE summary (max 20 words) of what customers think, mentioning the
strongest positive theme and the most common complaint if one exists. Use plain
Indian-English, no markdown, no quotes.

Then list exactly the top 3 recurring themes/keywords (2-4 words each, lowercase).

Return JSON like:
{"summary": "…", "keywords": ["…", "…", "…"]}

Reviews:
{reviews}"""


@retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def summarize_product(review_texts: List[str]) -> Tuple[str, List[str]]:
    """AI one-line summary + top-3 keywords for a product's reviews.

    Falls back to keyword frequency if the LLM is unavailable.
    """
    sample = review_texts[:40]
    if not sample:
        return "No customer reviews available yet.", []

    if settings.openai_api_key:
        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            joined = "\n".join(f"- {r[:220]}" for r in sample)
            response = await client.responses.create(
                model=settings.openai_model,
                instructions=_SUMMARY_PROMPT,
                input=joined,
                temperature=0.3,
            )
            import json

            parsed = json.loads(response.output_text.strip())
            summary = str(parsed.get("summary", ""))[:200] or "No summary generated."
            keywords = [str(k).lower() for k in parsed.get("keywords", [])][:5]
            return summary, keywords
        except Exception as exc:  # pragma: no cover
            logger.warning("OpenAI summary failed, using frequency fallback: %s", exc)

    # Fallback: theme frequency from the lexicon.
    from collections import Counter

    counter: Counter = Counter()
    for text in sample:
        lowered = text.lower()
        for word in set(_POSITIVE_WORDS | _NEGATIVE_WORDS):
            if len(word) > 2 and word in lowered:
                counter[word] += 1
    keywords = [w for w, _ in counter.most_common(5)]
    return f"Customers mention: {', '.join(keywords) if keywords else 'mixed feedback.'}", keywords


async def generate_market_summary(products, avg_sentiment: float) -> str:
    """One-line AI market summary across all tracked products."""
    if not settings.openai_api_key:
        label = "positive" if avg_sentiment >= 0.6 else "negative" if avg_sentiment <= 0.4 else "neutral"
        return (
            f"Market sentiment is {label} ({avg_sentiment:.0%} avg). "
            f"{len(products)} products tracked across smartphones, laptops and appliances."
        )
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        sample = "\n".join(
            f"- {p.name} ({p.brand}): ₹{p.current_price}, rating {p.rating}/5, "
            f"{p.review_count} reviews, discount {p.discount_pct:.0f}%"
            for p in products[:25]
        )
        response = await client.responses.create(
            model=settings.openai_model,
            instructions=(
                "You are a market analyst for Indian e-commerce (Flipkart/Amazon.in). "
                "Given product snapshots, write a 2-3 sentence market summary noting "
                "pricing, discount and sentiment trends. Plain text, no markdown."
            ),
            input=f"Avg sentiment score 0-1: {avg_sentiment:.2f}\n\n{sample}",
            temperature=0.4,
        )
        return response.output_text.strip()[:600]
    except Exception as exc:  # pragma: no cover
        logger.warning("Market summary generation failed: %s", exc)
        return "Unable to generate AI market summary this cycle."


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


async def process_reviews_batch(review_texts: List[str]):
    """Classify a batch concurrently. OpenAI default is 10 req/min on free tier,
    so we cap concurrency and batch with a small delay."""
    semaphore = asyncio.Semaphore(5)

    async def _one(text: str):
        async with semaphore:
            return await classify_review(text)

    # Chunk to stay under rate limits while keeping things live-ish.
    for i in range(0, len(review_texts), 8):
        chunk = review_texts[i : i + 8]
        yield await asyncio.gather(*(_one(t) for t in chunk))
