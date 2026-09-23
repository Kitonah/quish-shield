from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from PIL import Image
import tldextract

try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "brand_model.pth")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "brand_labels.json")
IMG_SIZE = 224

# Authorized domain whitelist per brand
BRAND_DOMAINS: Dict[str, List[str]] = {
    "sbi": ["onlinesbi.sbi", "sbi.co.in", "sbicardlogin.com"],
    "hdfc": ["hdfcbank.com", "hdfc.com"],
    "icici": ["icicibank.com", "icicicards.com"],
    "paytm": ["paytm.com"],
    "google": ["google.com", "google.co.in", "youtube.com", "youtu.be", "accounts.google.com"],
    "incometax": ["incometax.gov.in", "incometaxindiaefiling.gov.in"],
    "amazon": ["amazon.in", "amazon.com", "amazon.co.uk", "media-amazon.com"],
    "phonepe": ["phonepe.com"],
}

BRAND_DISPLAY_NAMES: Dict[str, Optional[str]] = {
    "sbi": "State Bank of India (SBI)",
    "hdfc": "HDFC Bank",
    "icici": "ICICI Bank",
    "paytm": "Paytm",
    "google": "Google",
    "incometax": "Income Tax India",
    "amazon": "Amazon",
    "phonepe": "PhonePe",
    "unknown": None,
}

BRAND_KEYWORDS: Dict[str, List[str]] = {
    "sbi": ["sbi", "state bank", "onlinesbi"],
    "hdfc": ["hdfc", "hdfcbank"],
    "icici": ["icici", "icicibank"],
    "paytm": ["paytm"],
    "google": ["google", "gmail", "youtube"],
    "incometax": ["income tax", "incometax", "e-filing", "efiling", "itr"],
    "amazon": ["amazon"],
    "phonepe": ["phonepe"],
}


@dataclass
class MatchResult:
    matched_brand: Optional[str] = None
    confidence: float = 0.0
    domain_matches: bool = True
    is_spoof: bool = False
    detail: str = "No known brand detected."
    method: str = "none"


class BrandVisualMatcher:
    def __init__(self):
        self.model = None
        self.class_names: List[str] = []
        self.device = None
        self.transform = None
        self.model_loaded = False
        self._try_load()

    def _try_load(self):
        if not TORCH_AVAILABLE or not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
            return

        try:
            with open(LABELS_PATH, "r") as f:
                self.class_names = json.load(f)

            num_classes = len(self.class_names)
            m = models.mobilenet_v2(weights=None)
            num_features = m.classifier[1].in_features
            m.classifier = nn.Sequential(
                nn.Dropout(p=0.3),
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(p=0.2),
                nn.Linear(256, num_classes),
            )

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            state_dict = torch.load(MODEL_PATH, map_location=self.device)
            m.load_state_dict(state_dict)
            m.eval()
            m.to(self.device)
            self.model = m

            self.transform = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self.model_loaded = True
            print(f"[VisualMatcher] Successfully initialized model with {num_classes} classes.")
        except Exception as e:
            print(f"[VisualMatcher] Initialization error: {e}")
            self.model_loaded = False

    def _predict_pil(self, img: Image.Image) -> Tuple[str, float]:
        try:
            tensor = self.transform(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                out = self.model(tensor)
                probs = torch.softmax(out, dim=1)[0]
                conf, idx = torch.max(probs, dim=0)
            return self.class_names[idx.item()], round(float(conf.item()) * 100.0, 2)
        except Exception:
            return "unknown", 0.0

    def predict_screenshot(self, screenshot_path: str) -> Tuple[str, float]:
        if not self.model_loaded or not screenshot_path or not os.path.exists(screenshot_path):
            return "unknown", 0.0

        try:
            full_img = Image.open(screenshot_path).convert("RGB")
            w, h = full_img.size

            # Pass 1: Focus on the top 35% where branding and header logos sit
            header_crop = full_img.crop((0, 0, w, int(h * 0.35)))
            h_brand, h_conf = self._predict_pil(header_crop)
            if h_brand != "unknown" and h_conf >= 75.0:
                return h_brand, h_conf

            # Pass 2: Whole page evaluation
            return self._predict_pil(full_img)
        except Exception:
            return "unknown", 0.0

    def is_official_domain(self, brand_key: str, url: str) -> bool:
        if brand_key not in BRAND_DOMAINS:
            return True

        ext = tldextract.extract(url)
        registered_domain = f"{ext.domain}.{ext.suffix}".lower() if ext.domain and ext.suffix else ""
        parsed_host = urlparse(url if "://" in url else f"http://{url}").netloc.lower().split(":")[0]

        allowed = BRAND_DOMAINS[brand_key]
        for legit in allowed:
            if registered_domain == legit or parsed_host == legit or parsed_host.endswith("." + legit):
                return True
        return False

    def _keyword_fallback(self, final_url: str, page_title: str) -> Tuple[str, float]:
        haystack = f"{final_url} {page_title}".lower()
        best_label = "unknown"
        best_score = 0.0

        for label, keywords in BRAND_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in haystack)
            if hits > 0:
                score = min(0.55 + (hits * 0.15), 0.85)
                if score > best_score:
                    best_score = score
                    best_label = label

        return best_label, best_score

    def compare_snapshot(
        self,
        screenshot_path: Optional[str],
        final_url: str,
        page_title: str = "",
    ) -> MatchResult:
        if self.model_loaded and screenshot_path and os.path.exists(screenshot_path):
            brand_key, conf_pct = self.predict_screenshot(screenshot_path)
            confidence = conf_pct / 100.0
            method = "cnn_model"
        else:
            brand_key, confidence = self._keyword_fallback(final_url, page_title)
            method = "keyword_fallback"

        if not brand_key or brand_key == "unknown" or confidence < 0.35:
            return MatchResult(method=method, detail="No visual brand impersonation detected.")

        display_name = BRAND_DISPLAY_NAMES.get(brand_key, brand_key.title())
        domain_legit = self.is_official_domain(brand_key, final_url)
        is_spoof = (not domain_legit) and (confidence >= 0.60)

        detail = (
            f"Page visually resembles '{display_name}' with {confidence * 100:.1f}% confidence ({method}). "
            f"{'Domain is legitimate.' if domain_legit else 'Domain does NOT match official brand portals!'}"
        )

        return MatchResult(
            matched_brand=display_name,
            confidence=round(confidence, 2),
            domain_matches=domain_legit,
            is_spoof=is_spoof,
            detail=detail,
            method=method,
        )


_matcher = BrandVisualMatcher()


def predict_brand(screenshot_path: str) -> Tuple[Optional[str], float]:
    brand, conf = _matcher.predict_screenshot(screenshot_path)
    return (brand, conf) if brand != "unknown" else (None, conf)


def compare_snapshot(screenshot_path: Optional[str], final_url: str, page_title: str = "") -> MatchResult:
    return _matcher.compare_snapshot(screenshot_path, final_url, page_title)