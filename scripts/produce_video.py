"""MAIS PMI Cockpit demo 動画 全自動制作 pipeline (action-then-narration timing model)。

4 段 orchestrator:
  1. AivisSpeech HTTP API (Style-Bert-VITS2、 まお おちついた speaker_id=888753763) で 16 scene raw narration WAV 生成
  2. Playwright (Chromium、 1920x1080) で uvicorn live demo flow を navigate + WebM 録画 + 各 scene action_elapsed 計測
  3. action_elapsed + settle buffer を lead-in silence にして per-scene padded WAV build (narration が settled page 上で 流れる timing 保証)
  4. ffmpeg で WebM + narration WAV → MP4 最終合成 (SRT 字幕 burn-in + 末尾 credit overlay + tpad で video 末尾 frame clone)

precondition (起動済 / install 済 verify):
  - uvicorn http://127.0.0.1:8001/health = 200
  - AivisSpeech engine http://127.0.0.1:10101/version = 200
    起動: `.vendor/aivis-engine/Windows-x64/run.exe --host 127.0.0.1 --port 10101`
  - ffmpeg (PATH 上、 `winget install Gyan.FFmpeg`)
  - playwright + chromium (`pip install -r requirements-video.txt && playwright install chromium`)

run:
  PYTHONIOENCODING=utf-8 python -m scripts.produce_video
  → out_video/mais_pmi_cockpit_demo.mp4 (約 2 分、 1080p、 約 8-9 MB)

env var (override 可):
  SPEAKER_ID=<int>     default 888753763 (まお おちついた)
  PITCH_SCALE=<float>  default 0.0、 ±0.03 が natural 域 (Style-Bert-VITS2 model 制限、 SSoT § 3)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

# Windows cp932 console で ✅/❌/日本語 print fail 防御 (T1/T2/T3 同 pattern、 cross-PJ universal)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ─── config ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "out_video"
TEMP_DIR = OUTPUT_DIR / "_temp"
UVICORN_URL = "http://127.0.0.1:8001"
ENGINE_URL = "http://127.0.0.1:10101"  # AivisSpeech-Engine standalone
SPEAKER_ID = int(os.environ.get("SPEAKER_ID", "888753763"))  # まお おちついた (cross-PJ 統一、 SSoT § 1)

LEAD_IN_SEC = 0.4    # legacy (--narration-only mode の fallback)
TRAIL_OUT_SEC = 0.4  # narration 終了から次 scene までの最低 silence
SETTLE_BUFFER_SEC = 0.3  # action 完了 (networkidle) 後 narration 開始 までの buffer (画面 settle 確保)

# pitchScale: AivisSpeech (Style-Bert-VITS2) は ±0.03 が natural 域、 超過で音割れ artifact (SSoT § 3)
PITCH_SCALE = float(os.environ.get("PITCH_SCALE", "0.0"))

VIEWPORT = {"width": 1920, "height": 1080}


# ─── scene definitions (id, duration_sec, action, narration_text) ────

@dataclass
class Scene:
    id: str
    duration: float
    action: Callable
    narration: str


def _scenes_factory() -> list[Scene]:
    """Playwright page を受け取り navigation を行う lambda 群を構築 (T4 100-day PMI cockpit demo)。

    pre-condition (script invocation 前):
      - uvicorn (port 8000) 起動済 (T4 src/api/app.py = FastAPI、 黒金 brand)
      - AivisSpeech (port 10101) 起動済

    T4 UI structure:
      - landing (/) = h1 + tagline + 5 feature panel + button「▶ 合成データで 100 日 cockpit 生成」 + dashboard link
      - cockpit_view (POST /generate) = CockpitProject meta + KPI 4 dim + KpiSnapshot + DriverInsight + NextAction
        + SentimentEvent + RetentionRisk + VendorContract / SaasLicense
      - dashboard_view (/dashboard) = Superset embed + KPI summary

    narration writing rules (video-pipeline SSoT § 3 順守):
      - 「、」 を 1 文 1-2 個 max、 単語間空白除去
      - jargon literal 漢字化 (PMI → 経営統合、 Isolation Forest → 異常値検知)
    """

    def s1(p):
        """landing top show (CRES Mantle T4 brand 提示)。"""
        p.goto(f"{UVICORN_URL}/")
        p.wait_for_load_state("networkidle")
        p.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")

    def s2(p):
        """tagline + Day-1 → Day-100 cockpit 提示 (slight scroll to expose tagline + first feature)。"""
        p.evaluate("window.scrollTo({top: 100, behavior: 'smooth'})")

    def s3(p):
        """feature ① Synergy KPI live dashboard (cost / revenue / cash_gen / working_capital)。"""
        p.evaluate(
            "document.querySelectorAll('.feature')[0]"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )

    def s4(p):
        """feature ② Driver Insight (Isolation Forest + LLM citation)。"""
        p.evaluate(
            "document.querySelectorAll('.feature')[1]"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )

    def s5(p):
        """feature ③ Next Action 推奨 (5 候補 ranked + 5 audience cascade)。"""
        p.evaluate(
            "document.querySelectorAll('.feature')[2]"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )

    def s6(p):
        """feature ④ Retention Risk + Sentiment (中堅日本企業 文化 fit 検知)。"""
        p.evaluate(
            "document.querySelectorAll('.feature')[3]"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )

    def s7(p):
        """feature ⑤ Vendor / SaaS 統合機会 自動抽出 (docling + 5-stage hybrid)。"""
        p.evaluate(
            "document.querySelectorAll('.feature')[4]"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )

    def s8(p):
        """button click → /generate POST → cockpit_view 表示 (T4 合成 cockpit 生成 実機 demo)。"""
        # scroll to button first
        p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        p.wait_for_timeout(600)
        p.evaluate(
            "document.querySelector('button[type=submit]')"
            ".scrollIntoView({behavior: 'smooth', block: 'center'})"
        )
        p.wait_for_timeout(400)
        # click + 遷移待ち (T4 data_gen で生成 = ~hundreds ms、 ただし safety で 90s timeout)
        p.locator("button:has-text('合成データで 100 日 cockpit 生成')").click(timeout=90000)
        p.wait_for_url("**/generate", timeout=90000)
        p.wait_for_load_state("networkidle", timeout=60000)

    def s9(p):
        """cockpit_view: top + CockpitProject meta (CP-id + Day-1 / Day-100 anchor date)。"""
        p.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")

    def s10(p):
        """cockpit_view: KpiDefinition 4 dim 表 (cost / revenue / cash_gen / working_capital)。"""
        p.evaluate(
            "[...document.querySelectorAll('h2')].find(h => h.textContent.includes('Synergy KPI Definition'))"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    def s11(p):
        """cockpit_view: KpiSnapshot time-series (100 日 × 4 KPI = 400 snapshot)。"""
        p.evaluate(
            "[...document.querySelectorAll('h2')].find(h => h.textContent.includes('KpiSnapshot'))"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    def s12(p):
        """cockpit_view: NextAction 推奨 (LangGraph orchestrator full DAG 出力)。"""
        p.evaluate(
            "[...document.querySelectorAll('h2')].find(h => h.textContent.includes('NextAction'))"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    def s13(p):
        """cockpit_view: SentimentEvent + RetentionRisk (中堅日本企業 文化 fit)。"""
        p.evaluate(
            "[...document.querySelectorAll('h2')].find(h => h.textContent.includes('RetentionRisk'))"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    def s14(p):
        """cockpit_view: VendorContract / SaasLicense 統合機会 (5 + 9 件)。"""
        p.evaluate(
            "[...document.querySelectorAll('h2')].find(h => h.textContent.includes('VendorContract'))"
            "?.scrollIntoView({behavior: 'smooth', block: 'start'})"
        )

    def s15(p):
        """dashboard_view: Superset embed (KPI summary + embed placeholder)。"""
        p.goto(f"{UVICORN_URL}/dashboard")
        p.wait_for_load_state("networkidle")
        p.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")

    def s16(p):
        """closing: 経営の責務を、 次の人へ (dashboard 末尾 deploy note へ scroll)。"""
        p.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")

    return [
        # narration 16 件 (video-pipeline SSoT § 3 順守: 「、」 max + 空白除去 + jargon 漢字化)
        # duration 初期値は低め、 auto-sync logic が actual WAV + margin に literal 上書き (SSoT § 2)
        Scene("S1", 6.5, s1, "マイス。経営統合100日進捗のエーアイのご紹介です。"),
        Scene("S2", 8.0, s2, "本ツールは買収成立後の初日から100日間、経営統合の進捗をAIが常時監視いたします。"),
        Scene("S3", 8.0, s3, "経営統合効果を4次元、原価、売上、現金創出、運転資本で常時可視化します。"),
        Scene("S4", 8.5, s4, "異常値検知AIが原因を自動抽出、根拠文書まで自動で紐付けて提示します。"),
        Scene("S5", 8.5, s5, "次の打ち手を5候補、5つの対象別に通知文書まで自動起草します。"),
        Scene("S6", 8.0, s6, "退職予兆と組織感情を自動検知、中堅日本企業特有の文化適合も評価します。"),
        Scene("S7", 8.5, s7, "重複した取引先と未活用ライセンスを自動抽出、統合機会を逃しません。"),
        Scene("S8", 8.0, s8, "では実機で生成例をご覧ください。"),
        Scene("S9", 7.0, s9, "100日進捗の起点と期日が自動算定、対象企業の業種規模も継承します。"),
        Scene("S10", 8.0, s10, "経営統合効果の4次元、目標値も100日後時点で自動設定されます。"),
        Scene("S11", 7.5, s11, "日次計測値は100日かける4次元、合計400件で時系列推移を蓄積します。"),
        Scene("S12", 8.0, s12, "次の打ち手も担当部署と通知対象が自動付与、5候補ランキング付きです。"),
        Scene("S13", 7.5, s13, "退職リスク点数化と感情分析を組合せ、文化適合の課題を早期surface化します。"),
        Scene("S14", 8.0, s14, "取引先5社、ライセンス9件、稼働率まで含めて統合判断材料を提示します。"),
        Scene("S15", 7.5, s15, "経営層向け画面はApache Superset組込みで、JWT認証経由で常時最新です。"),
        Scene("S16", 8.0, s16, "マイス。経営の責務を、次の人へ。ご清聴ありがとうございました。"),
    ]


SCENES = _scenes_factory()


# ─── helpers (T1/T2/T3 literal inherit、 cross-PJ universal) ──────────

def info(msg: str) -> None:
    print(f"[produce_video] {msg}", flush=True)


def check_preconditions() -> None:
    """uvicorn / AivisSpeech / ffmpeg / playwright + chromium の起動確認 (T1/T2/T3 literal inherit)。"""
    errors = []

    try:
        r = requests.get(f"{UVICORN_URL}/health", timeout=3)
        assert r.status_code == 200
        info(f"OK uvicorn live ({UVICORN_URL}/health = 200)")
    except Exception as e:
        errors.append(f"uvicorn 起動不能: {UVICORN_URL} ({e}). 別 shell で uvicorn を起動してください")

    try:
        r = requests.get(f"{ENGINE_URL}/version", timeout=3)
        assert r.status_code == 200
        info(f"OK AivisSpeech engine live ({ENGINE_URL}/version = {r.text.strip()})")
    except Exception as e:
        hint = ".vendor/aivis-engine/Windows-x64/run.exe --host 127.0.0.1 --port 10101 で起動してください (T1/T2/T3 binary cross-PJ 共有可)"
        errors.append(f"AivisSpeech engine 起動不能: {ENGINE_URL} ({e}). {hint}")

    if shutil.which("ffmpeg") is None:
        errors.append("ffmpeg が PATH に不在。 `winget install Gyan.FFmpeg` で install してください")
    else:
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")

    try:
        from playwright.sync_api import sync_playwright  # noqa
        info("OK playwright (Python binding)")
    except ImportError:
        errors.append("playwright 未 install。 `pip install playwright && playwright install chromium` を実行してください")

    if errors:
        info("==== precondition error ====")
        for e in errors:
            info(f"  - {e}")
        sys.exit(1)


def aivis_synthesize(text: str) -> bytes:
    """AivisSpeech HTTP API で WAV bytes 生成 (Style-Bert-VITS2、 素 AI prosody、 T1/T2/T3 literal inherit)。"""
    q = requests.post(
        f"{ENGINE_URL}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=15,
    )
    q.raise_for_status()
    q_json = q.json()
    if PITCH_SCALE != 0.0:
        q_json["pitchScale"] = PITCH_SCALE
    s = requests.post(
        f"{ENGINE_URL}/synthesis",
        params={"speaker": SPEAKER_ID},
        json=q_json,
        timeout=60,
    )
    s.raise_for_status()
    return s.content


def ffprobe_duration(path: Path) -> float:
    """ffprobe で WAV/WebM の長さ秒を取得 (T1/T2/T3 literal inherit)。"""
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    )
    return float(out.decode().strip())


def make_padded_wav(scene: Scene, raw_wav_path: Path, out_path: Path, lead_in_sec: float | None = None) -> None:
    """raw WAV を scene.duration に合わせて lead-in + trail-out silence で sandwich pad (T1/T2/T3 literal inherit)。"""
    lead = LEAD_IN_SEC if lead_in_sec is None else lead_in_sec
    raw_dur = ffprobe_duration(raw_wav_path)
    if raw_dur > scene.duration - lead - TRAIL_OUT_SEC:
        info(f"  WARN [{scene.id}] narration {raw_dur:.2f}s が scene {scene.duration:.1f}s (lead={lead:.2f}s) に対し tight、 trail_out 縮小")

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(raw_wav_path),
            "-af", f"adelay={int(lead * 1000)}|{int(lead * 1000)},apad=whole_dur={scene.duration}",
            "-ar", "24000", "-ac", "1",
            str(out_path),
        ],
        check=True,
    )


def concat_narration(scene_padded_wavs: list[Path], out_path: Path) -> None:
    """全 scene padded WAV を concat demuxer で 1 本に結合 (T1/T2/T3 literal inherit)。"""
    concat_list = TEMP_DIR / "concat_audio.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in scene_padded_wavs),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(out_path),
        ],
        check=True,
    )


def record_demo() -> Path:
    """Playwright action-then-narration model で demo flow 録画、 WebM path 返却。

    各 scene で action() → wait_for_load_state networkidle → scene.action_elapsed 計測 →
    narration_window (= raw_dur + SETTLE_BUFFER + TRAIL_OUT) wait。 narration が settled
    destination page 上で 流れる timing 保証 (timing drift 構造的解消)。
    """
    from playwright.sync_api import sync_playwright

    info("Playwright Chromium 起動中... (action-then-narration timing mode)")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(TEMP_DIR),
            record_video_size=VIEWPORT,
        )
        page = context.new_page()

        for scene in SCENES:
            raw_dur = getattr(scene, "raw_duration", 0.0)
            info(f"  [{scene.id}] action: {scene.narration[:30]}... (narration_raw={raw_dur:.2f}s)")
            t0 = time.time()
            scene.action(page)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            scene.action_elapsed = time.time() - t0
            narration_window_sec = raw_dur + SETTLE_BUFFER_SEC + TRAIL_OUT_SEC
            info(f"    action_elapsed={scene.action_elapsed:.2f}s, narration_window={narration_window_sec:.2f}s")
            page.wait_for_timeout(int(narration_window_sec * 1000))

        context.close()
        browser.close()

    webms = sorted(TEMP_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not webms:
        raise RuntimeError(f"WebM が {TEMP_DIR} に生成されなかった")
    return webms[-1]


def _fmt_srt_time(t: float) -> str:
    """SRT timestamp 形式 (HH:MM:SS,mmm) (T1/T2/T3 literal inherit)。"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def generate_srt(out_path: Path) -> None:
    """16 scene narration を SRT 形式に literal 出力。action_elapsed set 済なら action-aware lead 使用。"""
    lines: list[str] = []
    cum = 0.0
    for i, scene in enumerate(SCENES, 1):
        action_elapsed = getattr(scene, "action_elapsed", None)
        lead = (action_elapsed + SETTLE_BUFFER_SEC) if action_elapsed is not None else LEAD_IN_SEC
        start = cum + lead
        end = cum + scene.duration - TRAIL_OUT_SEC
        cum += scene.duration
        lines.append(f"{i}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{scene.narration}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def compose_final(webm: Path, narration: Path, out_mp4: Path) -> None:
    """WebM + narration WAV → MP4 (1080p / H.264 / AAC) + 字幕 burn-in + 末尾クレジット overlay (T1/T2/T3 literal inherit)。

    drawtext / subtitles escape 戦略 + 末尾 7 秒 enable + Yu Gothic UI Bold + MarginV=30 全 T1/T2/T3 同 logic。
    """
    credit_path = TEMP_DIR / "credit.txt"
    credit_path.write_text(
        "MAIS PMI Cockpit (PoC) / AivisSpeech: まお おちついた / 合成データ only",
        encoding="utf-8",
    )

    srt_path = TEMP_DIR / "narration.srt"
    generate_srt(srt_path)

    fontfile_escaped = "C\\:/Windows/Fonts/YuGothM.ttc"
    textfile_escaped = credit_path.as_posix().replace(":", "\\:")
    srt_escaped = srt_path.as_posix().replace(":", "\\:")

    narration_dur = ffprobe_duration(narration)
    video_dur = ffprobe_duration(webm)
    enable_from = max(0.0, narration_dur - 7.0)
    pad_sec = max(0.0, narration_dur - video_dur + 0.2)
    tpad_filter = f"tpad=stop_mode=clone:stop_duration={pad_sec:.2f}" if pad_sec > 0.01 else None

    subtitles_filter = (
        f"subtitles='{srt_escaped}':"
        "force_style='FontName=Yu Gothic UI Semibold,"
        "Fontsize=22,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
        "BackColour=&H80000000&,BorderStyle=1,Outline=2,Shadow=1,"
        "MarginV=30,Alignment=2'"
    )

    drawtext_filter = (
        f"drawtext=fontfile='{fontfile_escaped}':"
        f"textfile='{textfile_escaped}':"
        "fontcolor=white:fontsize=26:"
        "x=(w-text_w)/2:y=h-th-40:"
        "box=1:boxcolor=black@0.75:boxborderw=14:"
        f"enable='gte(t,{enable_from:.2f})'"
    )

    vf_parts = [f for f in (tpad_filter, subtitles_filter, drawtext_filter) if f]
    vf_chain = ",".join(vf_parts)
    if tpad_filter:
        info(f"  tpad: video {video_dur:.2f}s → narration {narration_dur:.2f}s (clone {pad_sec:.2f}s 末尾 frame)")

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(webm),
            "-i", str(narration),
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-metadata", f"comment=AivisSpeech:speaker_id={SPEAKER_ID} / MAIS PMI Cockpit PoC / synthetic data only",
            str(out_mp4),
        ],
        check=True,
    )


# ─── main orchestrator ───────────────────────────────────────────────

def main() -> int:
    narration_only = "--narration-only" in sys.argv
    info("=== MAIS PMI Cockpit demo video pipeline (action-then-narration model) ===")
    if narration_only:
        info("(--narration-only mode: AivisSpeech synthesis のみ実行、 Playwright + ffmpeg compose skip)")
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    info("\n[0/3] precondition check")
    if narration_only:
        try:
            r = requests.get(f"{ENGINE_URL}/version", timeout=3)
            assert r.status_code == 200
            info(f"OK AivisSpeech engine live ({ENGINE_URL}/version = {r.text.strip()})")
        except Exception as e:
            info(f"AivisSpeech engine 起動不能: {ENGINE_URL} ({e})")
            sys.exit(1)
        if shutil.which("ffmpeg") is None:
            info("ffmpeg が PATH に不在")
            sys.exit(1)
        info(f"OK ffmpeg ({shutil.which('ffmpeg')})")
    else:
        check_preconditions()

    info(f"\n[1/4] AivisSpeech で {len(SCENES)} scene の raw narration WAV 生成 (padding は phase 3 で)")
    for scene in SCENES:
        raw = TEMP_DIR / f"{scene.id}_raw.wav"
        wav_bytes = aivis_synthesize(scene.narration)
        raw.write_bytes(wav_bytes)
        scene.raw_duration = ffprobe_duration(raw)
        info(f"  [{scene.id}] raw_duration={scene.raw_duration:.2f}s ({scene.narration[:25]}...)")

    if narration_only:
        info("\n[narration-only fallback] padded WAV を legacy fixed lead で build")
        padded_wavs: list[Path] = []
        for scene in SCENES:
            raw = TEMP_DIR / f"{scene.id}_raw.wav"
            padded = TEMP_DIR / f"{scene.id}_padded.wav"
            scene.duration = round(scene.raw_duration + LEAD_IN_SEC + TRAIL_OUT_SEC + 0.3, 1)
            make_padded_wav(scene, raw, padded)
            padded_wavs.append(padded)
        narration_wav = TEMP_DIR / "narration_full.wav"
        concat_narration(padded_wavs, narration_wav)
        listen_path = OUTPUT_DIR / "narration_only_preview.wav"
        shutil.copy(narration_wav, listen_path)
        total_audio = ffprobe_duration(narration_wav)
        info("\n=== --narration-only Done ===")
        info(f"  preview WAV: {listen_path.relative_to(BASE_DIR)} ({total_audio:.2f}s)")
        return 0

    info(f"\n[2/4] Playwright で demo flow 録画 (action-then-narration model、 scene.action_elapsed 計測)")
    webm = record_demo()
    video_dur = ffprobe_duration(webm)
    info(f"  WebM: {webm.name} = {video_dur:.2f}s")
    info(f"  action_elapsed per scene (settled state 到達 wall-clock):")
    for scene in SCENES:
        info(f"    [{scene.id}] action_elapsed={scene.action_elapsed:.2f}s")

    info(f"\n[3/4] padded WAV build (lead_in = action_elapsed + {SETTLE_BUFFER_SEC}s settle buffer)")
    padded_wavs: list[Path] = []
    for scene in SCENES:
        raw = TEMP_DIR / f"{scene.id}_raw.wav"
        padded = TEMP_DIR / f"{scene.id}_padded.wav"
        lead = scene.action_elapsed + SETTLE_BUFFER_SEC
        scene.duration = round(lead + scene.raw_duration + TRAIL_OUT_SEC, 2)
        make_padded_wav(scene, raw, padded, lead_in_sec=lead)
        padded_wavs.append(padded)
        info(f"  [{scene.id}] lead={lead:.2f}s + raw={scene.raw_duration:.2f}s + trail={TRAIL_OUT_SEC}s = scene.duration={scene.duration}s")

    narration_wav = TEMP_DIR / "narration_full.wav"
    concat_narration(padded_wavs, narration_wav)
    total_audio = ffprobe_duration(narration_wav)
    info(f"  narration 結合完了: {narration_wav.name} = {total_audio:.2f}s (video {video_dur:.2f}s と 同期想定)")

    info("\n[4/4] ffmpeg で MP4 最終合成 + 末尾クレジット overlay + SRT burn-in")
    out_mp4 = OUTPUT_DIR / "mais_pmi_cockpit_demo.mp4"
    compose_final(webm, narration_wav, out_mp4)
    final_dur = ffprobe_duration(out_mp4)
    size_mb = out_mp4.stat().st_size / 1024 / 1024
    info(f"  完成: {out_mp4} = {final_dur:.2f}s / {size_mb:.1f} MB")

    info("\n=== Done ===")
    info(f"動画 = {out_mp4.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
