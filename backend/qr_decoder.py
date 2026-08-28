import cv2
import numpy as np
import re
import requests

class QRDecoder:
    @staticmethod
    def resolve_url(url: str, timeout: int = 5) -> str:
        try:
            response = requests.head(url, allow_redirects=True, timeout=timeout)
            return response.url
        except Exception:
            return url

    @classmethod
    def decode_image(cls, image_bytes: bytes) -> dict:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        
        if not data:
            return {"found": False, "raw_data": None, "resolved_url": None, "is_upi": False}
            
        resolved = cls.resolve_url(data) if data.startswith(("http://", "https://")) else data
        return {
            "found": True,
            "raw_data": data,
            "resolved_url": resolved,
            "is_upi": data.startswith("upi://")
        }

    @classmethod
    def parse_sms(cls, text: str) -> list[dict]:
        url_pattern = r"(https?://[^\s]+)"
        urls = re.findall(url_pattern, text)
        return [{"original": u, "resolved": cls.resolve_url(u)} for u in urls]