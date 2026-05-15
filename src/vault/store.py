"""T4 PII Vault: Fernet 暗号化 + audit log。

試作 = Fernet (AES-128-CBC + HMAC-SHA256) で JSONL 暗号化、 移植 = KMS + envelope key 化。
kpi / anomaly / driver / next_action / sentiment / vendor / dashboard / pipeline / citation / operational / integration / api
は本 module literal import 禁止 (module boundary check)。

T4 specific vault content:
- retention_risk_pii: 退職 risk 個人 sentiment quote (SentimentEvent.excerpt_redacted の raw 化)
- vendor_pii: vendor 契約 個別条項 (NDA 機密、 redact 後 op DB へ)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def _data_dir() -> Path:
    """env から DATA_DIR を lazy read (test 環境で env override 可能)。"""
    return Path(os.environ.get("DATA_DIR", "./data"))


def _vault_dir() -> Path:
    return _data_dir() / "vault"


def _audit_dir() -> Path:
    return _data_dir() / "audit"


def _audit_log_path() -> Path:
    return _audit_dir() / "access_log.jsonl"


def _get_key() -> bytes:
    """VAULT_KEY env を取得 (試作)、 未設定なら literal RuntimeError + 生成 hint。"""
    key_str = os.environ.get("VAULT_KEY")
    if not key_str:
        key = Fernet.generate_key()
        raise RuntimeError(
            f"VAULT_KEY 未設定。 .env に下記を追記:\n"
            f" VAULT_KEY={key.decode()}\n"
            f"(試作用、 移植時は AWS KMS / Cloud KMS に置換)"
        )
    return key_str.encode()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_audit(action: str, item_id: str, requester: str = "system", reason: str = "") -> None:
    """全 vault access を audit log に append。"""
    _audit_dir().mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _now_iso(),
        "action": action,
        "item_id": item_id,
        "requester": requester,
        "reason": reason,
    }
    with _audit_log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def encrypt_to_vault(
    item_id: str, data: dict[str, Any], vault_name: str = "retention_risk_pii"
) -> Path:
    """data dict を Fernet encrypt + vault file に append。 audit log 同時 emit。

    T4 default vault_name = retention_risk_pii (RetentionRisk PII)、
    vendor_pii / cockpit_project_pii も同 pattern。
    """
    _vault_dir().mkdir(parents=True, exist_ok=True)
    cipher = Fernet(_get_key())
    vault_path = _vault_dir() / f"{vault_name}.enc"

    plaintext = json.dumps({"item_id": item_id, "data": data}, ensure_ascii=False)
    ciphertext = cipher.encrypt(plaintext.encode("utf-8"))

    with vault_path.open("ab") as f:
        f.write(ciphertext + b"\n")

    emit_audit("write", item_id, requester="vault_store", reason=f"encrypt_to_{vault_name}")
    return vault_path


def decrypt_from_vault(
    item_id: str,
    vault_name: str = "retention_risk_pii",
    requester: str = "system",
    reason: str = "",
) -> dict[str, Any] | None:
    """vault file から item_id match を decrypt 返却 (literal one-by-one、 PoC linear scan)。

    本番 = SQLCipher / DB index で O(log n) literal upgrade。
    """
    vault_path = _vault_dir() / f"{vault_name}.enc"
    if not vault_path.exists():
        emit_audit("read_miss", item_id, requester=requester, reason=reason + " (vault unavailable)")
        return None

    cipher = Fernet(_get_key())
    with vault_path.open("rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                plain = cipher.decrypt(line).decode("utf-8")
                record = json.loads(plain)
                if record.get("item_id") == item_id:
                    emit_audit("read", item_id, requester=requester, reason=reason)
                    return record.get("data")
            except (InvalidToken, json.JSONDecodeError):
                continue

    emit_audit("read_miss", item_id, requester=requester, reason=reason + " (not found)")
    return None
