import base64
import hashlib
import json
import platform
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class LicenseStatus:
    valid: bool
    message: str
    expires_at: int = 0
    license_id: str = ""


def device_id():
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _verify_ed25519(payload, signature, public_key):
    if not public_key or not signature:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key))
        key.verify(base64.b64decode(signature), _canonical(payload))
        return True
    except Exception:
        return False


class LicenseManager:
    """Client-side license contract; the server owns activation and billing."""

    def __init__(self, config):
        self.endpoint = str(config.get("license_server_url", "")).rstrip("/")
        self.public_key = str(config.get("license_public_key", ""))

    def validate(self, license_key, device_id, timeout=10):
        if not self.endpoint:
            return LicenseStatus(False, "Chưa cấu hình license server.")
        body = json.dumps({"license_key": license_key, "device_id": device_id}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}/v1/licenses/validate", data=body,
            headers={"Content-Type": "application/json", "User-Agent": "TikTokVideoManager"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            return LicenseStatus(False, f"Không kết nối được license server: {error}")
        payload = result.get("payload", {})
        if not result.get("valid") or not _verify_ed25519(payload, result.get("signature"), self.public_key):
            return LicenseStatus(False, "License không hợp lệ hoặc chữ ký không đúng.")
        expires_at = int(payload.get("expires_at", 0))
        if expires_at <= int(time.time()):
            return LicenseStatus(False, "License đã hết hạn.", expires_at, str(payload.get("license_id", "")))
        return LicenseStatus(True, "License hợp lệ.", expires_at, str(payload.get("license_id", "")))
