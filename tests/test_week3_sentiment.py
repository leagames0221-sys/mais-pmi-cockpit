"""Week 3 SentimentEvent test (mock sentiment + topic + Slack/Teams/アンケート connector)。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.llm.provider import MockProvider
from src.sentiment.analyze_message import (
    analyze_message,
    batch_analyze_messages,
    generate_mock_messages,
    mock_sentiment_score,
    mock_topic_tags,
    try_transformers_available,
)


# ─── mock_sentiment_score ──────────────────────────────────────────────

def test_mock_sentiment_score_negative():
    score = mock_sentiment_score("退職を検討しています、 待遇面の不満があります")
    assert score < 0


def test_mock_sentiment_score_positive():
    score = mock_sentiment_score("満足度が向上して、 期待しています")
    assert score > 0


def test_mock_sentiment_score_neutral():
    score = mock_sentiment_score("会議の予定は明日です")
    assert score == 0.0


# ─── mock_topic_tags ──────────────────────────────────────────────────

def test_mock_topic_tags_jp_day1_retention_axis():
    """T3 JPDay1Pattern「組合対応」軸 analogical、 keyword match で literal 認識。"""
    tags = mock_topic_tags("組合との対話が活発化")
    assert "組合対応" in tags


def test_mock_topic_tags_human_resources():
    tags = mock_topic_tags("給与改定について、 待遇 が改善")
    assert "給与待遇" in tags


def test_mock_topic_tags_unspecified():
    tags = mock_topic_tags("ランチに何を食べようか")
    assert tags == ["unspecified"]


# ─── analyze_message ──────────────────────────────────────────────────

def test_analyze_message_slack():
    se = analyze_message(
        cp_id="CP-000001",
        source_channel="slack",
        message_text="退職を検討しています、 不満が解消されないため",
        observed_at=datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc),
        se_seq=1,
        provider=MockProvider(),
    )
    assert se.se_id == "SE-000001"
    assert se.cp_id == "CP-000001"
    assert se.source_channel == "slack"
    assert se.sentiment_score < 0  # negative
    assert "退職" in se.topic_tag
    assert "(redacted excerpt)" in se.excerpt_redacted


def test_analyze_message_teams():
    se = analyze_message(
        cp_id="CP-000001",
        source_channel="teams",
        message_text="新体制の方針が前向きで嬉しい変化",
        se_seq=1,
        provider=MockProvider(),
    )
    assert se.source_channel == "teams"
    assert se.sentiment_score > 0


def test_analyze_message_survey():
    se = analyze_message(
        cp_id="CP-000001",
        source_channel="survey",
        message_text="残業負荷について懸念があります",
        se_seq=1,
        provider=MockProvider(),
    )
    assert se.source_channel == "survey"
    assert "業務負荷" in se.topic_tag


def test_analyze_message_pii_redaction_excerpt():
    """message_text → excerpt_redacted に (redacted excerpt) prefix literal 付与 (PII boundary 順守)。"""
    se = analyze_message(
        cp_id="CP-000001",
        source_channel="slack",
        message_text="tanaka@example.com に連絡、 電話 090-1234-5678",
        se_seq=1,
    )
    # PoC simplification: prefix で literal mark、 Week 4 で full Presidio redaction swap
    assert "(redacted excerpt)" in se.excerpt_redacted


# ─── batch + connector ────────────────────────────────────────────────

def test_batch_analyze_messages():
    messages = generate_mock_messages(cp_id="CP-000001", n=10)
    events = batch_analyze_messages(cp_id="CP-000001", messages=messages, start_seq=1, provider=MockProvider())
    assert len(events) == 10
    # 全 events に se_id sequential
    for i, e in enumerate(events, start=1):
        assert e.se_id == f"SE-{i:06d}"
    # source_channel mix (slack / teams / survey)
    channels = {e.source_channel for e in events}
    assert len(channels) >= 2  # 3 channel mix の高い確率


def test_generate_mock_messages_seed_repeatable():
    a = generate_mock_messages(cp_id="CP-000001", n=5)
    b = generate_mock_messages(cp_id="CP-000001", n=5)
    # seed 固定 (cp_id + 20260513) で literal 同 sequence
    assert [m["message_text"] for m in a] == [m["message_text"] for m in b]


def test_try_transformers_available():
    """transformers / torch import 可能性 verify (Week 4 で full active 確認用)。"""
    result = try_transformers_available()
    assert isinstance(result, bool)
