"""Sentiment analysis (HF Transformers + LLMProvider 多軸分析 + Slack/Teams/アンケート mock connector、 ADR-301 + ADR-305 順守)。

Stage 構成:
  Stage A: HF Transformers multilingual sentiment base (Apache-2.0 model 限定採用、 optional heavy import)
  Stage B: LLMProvider 多軸分析 (topic_tag 抽出 + sentiment grounding、 試作 = MockProvider)
  Stage C: Slack/Teams/アンケート connector (Week 3 PoC = mock、 Week 4 で real API 連携 path)

PoC default behavior:
  - mock sentiment (token-based heuristic) で deterministic literal active
  - HF Transformers = optional (Week 4 で actual model load swap)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

from src.llm.provider import LLMProvider, default_provider
from src.schema.types import SentimentEvent


# ─── HF Transformers availability check ────────────────────────────────

def try_transformers_available() -> bool:
    """transformers + torch 利用可能 verify (Week 4 で full active path 確認用)。"""
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


# ─── mock sentiment heuristic (Week 3 PoC、 deterministic) ─────────────

NEGATIVE_TOKENS = {"不安", "心配", "怒り", "不満", "辞職", "退職", "苦情", "問題", "懸念", "ストレス", "悲しい", "嫌"}
POSITIVE_TOKENS = {"満足", "嬉しい", "楽しい", "素晴らしい", "感謝", "ありがとう", "良い", "期待", "前向き"}
TOPIC_KEYWORDS = {
    "人事制度変更": ["人事", "制度", "改定", "組織変更"],
    "給与待遇": ["給与", "給料", "賞与", "待遇", "ボーナス"],
    "退職": ["退職", "辞職", "辞める"],
    "組合対応": ["組合", "労組", "団交", "労使"],
    "上司関係": ["上司", "マネージャ", "課長", "部長"],
    "業務負荷": ["残業", "過労", "負荷", "忙しい"],
}


def mock_sentiment_score(text: str) -> float:
    """token-based heuristic で sentiment score (-1.0 ~ 1.0) literal 算出 (Week 3 PoC default)。"""
    neg = sum(1 for t in NEGATIVE_TOKENS if t in text)
    pos = sum(1 for t in POSITIVE_TOKENS if t in text)
    if neg == 0 and pos == 0:
        return 0.0
    total = neg + pos
    return round((pos - neg) / total, 2)


def mock_topic_tags(text: str) -> list[str]:
    """topic keyword match で tag literal 抽出 (Week 3 PoC default、 Week 4 で LLM 多軸分析 swap)。"""
    tags = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(topic)
    return tags or ["unspecified"]


# ─── Sentiment analyze entry ──────────────────────────────────────────

def _seq_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:06d}"


def _redact_excerpt(text: str, max_chars: int = 80) -> str:
    """raw text → redact (簡略 PoC: 文字数 truncate + placeholder)。

    実 Presidio 経由 PII redaction は Week 4 で full active (doctrine: prior-art-first 順守、 T1/T2/T3 inherit pattern)。
    """
    if len(text) <= max_chars:
        return f"(redacted excerpt) {text[:max_chars]}"
    return f"(redacted excerpt) {text[:max_chars]}..."


def analyze_message(
    cp_id: str,
    source_channel: Literal["slack", "teams", "survey"],
    message_text: str,
    observed_at: Optional[datetime] = None,
    se_seq: int = 1,
    provider: Optional[LLMProvider] = None,
) -> SentimentEvent:
    """1 message → 1 SentimentEvent 抽出 (mock sentiment + topic + redacted excerpt)。"""
    if observed_at is None:
        observed_at = datetime.now(timezone.utc)
    if provider is None:
        provider = default_provider()

    score = mock_sentiment_score(message_text)
    tags = mock_topic_tags(message_text)
    excerpt = _redact_excerpt(message_text)

    return SentimentEvent(
        se_id=_seq_id("SE", se_seq),
        cp_id=cp_id,
        source_channel=source_channel,
        observed_at=observed_at,
        sentiment_score=score,
        topic_tag=tags,
        excerpt_redacted=excerpt,
    )


def batch_analyze_messages(
    cp_id: str,
    messages: list[dict],
    start_seq: int = 1,
    provider: Optional[LLMProvider] = None,
) -> list[SentimentEvent]:
    """複数 message → SentimentEvent list (orchestrator から call)。

    messages dict format: {"source_channel": "slack"|"teams"|"survey", "message_text": str, "observed_at": datetime}
    """
    events: list[SentimentEvent] = []
    for i, m in enumerate(messages):
        events.append(analyze_message(
            cp_id=cp_id,
            source_channel=m["source_channel"],
            message_text=m["message_text"],
            observed_at=m.get("observed_at"),
            se_seq=start_seq + i,
            provider=provider,
        ))
    return events


# ─── Mock connector data (Week 3 PoC、 Week 4 で real Slack/Teams API 連携) ─

def generate_mock_messages(cp_id: str, n: int = 10) -> list[dict]:
    """合成 message list 生成 (PoC test fixture、 Slack/Teams/アンケート mix)。"""
    import random
    rng = random.Random(20260513 + hash(cp_id) % 10000)
    channels = ["slack", "teams", "survey"]
    sample_texts = [
        "新体制発足について、 担当部署からの説明がまだなく不安があります",
        "今期の人事制度改定は前向きに受け止めています、 感謝です",
        "残業が増えていて、 負荷が高い状況が続いています",
        "上司との 1on1 が増えて満足度が向上しました",
        "退職を検討しています、 待遇面の不満が解消されないため",
        "組合との対話が活発化していて良い兆候です",
        "新しい福利厚生制度は嬉しい変化です",
        "業務の引き継ぎが進まず、 ストレスを感じています",
        "今後のキャリアパスについて懸念があります",
        "全社的な方向性が明確になり、 期待しています",
    ]
    messages = []
    for i in range(n):
        messages.append({
            "source_channel": rng.choice(channels),
            "message_text": rng.choice(sample_texts),
            "observed_at": datetime(2026, 9, 15 + i % 30, 10, 0, 0, tzinfo=timezone.utc),
        })
    return messages
