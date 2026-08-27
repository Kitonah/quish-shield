"""
+======================================================================+
|  QuiShield -- Member 4: Visual / Brand Matcher (UPGRADED)            |
|                                                                      |
|  WHAT THIS FILE DOES (in plain English):                             |
|  This is the REAL version of the visual matcher. Instead of just     |
|  checking keywords in the URL, it actually LOOKS at the screenshot   |
|  using a trained neural network (MobileNetV2) and says:              |
|    "This page looks 87% like an SBI login page."                     |
|                                                                      |
|  If the model file (brand_model.pth) hasn't been created yet         |
|  (i.e., you haven't run train_model.py), it falls back to the        |
|  old keyword-based matching so nothing breaks.                       |
|                                                                      |
|  INTEGRATION:                                                        |
|  The class name (BrandVisualMatcher) and method signature            |
|  (compare_snapshot) are IDENTICAL to the old mock version.           |
|  No other file needs to change.                                      |
+======================================================================+
"""

import os
import json
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

# Image handling
from PIL import Image

# PyTorch (only imported if model exists, with fallback)
try:
    import torch
    import torch.nn as nn
    from torchvision import transforms, models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ---- Paths -------------------------------------------------------------------

MODEL_PATH = os.path.join(os.path.dirname(__file__), "brand_model.pth")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "brand_labels.json")

# Image size MobileNetV2 expects
IMG_SIZE = 224


# ---- Known brand domains (used for spoof detection) --------------------------
# Even with the model, we still need to know the REAL domain for each brand
# to decide if the page is a spoof (looks like SBI but hosted on a fake domain).

BRAND_DOMAINS = {
    "sbi":       ["onlinesbi.sbi", "sbi.co.in", "sbicardlogin.com"],
    "hdfc":      ["hdfcbank.com"],
    "icici":     ["icicibank.com", "icicicards.com"],
    "paytm":     ["paytm.com"],
    "google":    ["google.com", "gmail.com", "accounts.google.com"],
    "incometax": ["incometax.gov.in"],
    "amazon":    ["amazon.in", "amazon.com"],
    "phonepe":   ["phonepe.com"],
}

# Human-readable brand names
BRAND_DISPLAY_NAMES = {
    "sbi":       "State Bank of India (SBI)",
    "hdfc":      "HDFC Bank",
    "icici":     "ICICI Bank",
    "paytm":     "Paytm",
    "google":    "Google",
    "incometax": "Income Tax India",
    "amazon":    "Amazon India",
    "phonepe":   "PhonePe",
    "unknown":   None,
}


# ---- Fallback keyword matching (same as old mock) ----------------------------

BRAND_KEYWORDS = {
    "sbi":       ["sbi", "state bank", "onlinesbi"],
    "hdfc":      ["hdfc", "hdfcbank"],
    "icici":     ["icici", "icicibank"],
    "paytm":     ["paytm"],
    "google":    ["google", "gmail"],
    "incometax": ["income tax", "incometax", "e-filing", "efiling", "itr"],
    "amazon":    ["amazon"],
    "phonepe":   ["phonepe"],
}


# ---- Data class for the match result ----------------------------------------

@dataclass
class MatchResult:
    """
    What the visual matcher returns for each check.

    Fields explained:
      matched_brand   : The brand it thinks the page is imitating
                        (None if no match found).
      confidence       : A number from 0.0 to 1.0.
                        0.0 = definitely not a copycat.
                        1.0 = looks exactly like the real site.
      domain_matches   : Does the URL actually belong to the
                        real brand? True = legit, False = suspicious.
      is_spoof         : True if it LOOKS like a brand but the
                        URL does NOT belong to that brand.
      detail           : A human-readable explanation.
      method           : "model" or "keyword" -- which approach was used.
    """
    matched_brand:  Optional[str] = None
    confidence:     float         = 0.0
    domain_matches: bool          = True
    is_spoof:       bool          = False
    detail:         str           = "No known brand detected."
    method:         str           = "keyword"


# ---- The Visual Matcher Class ------------------------------------------------

class BrandVisualMatcher:
    """
    Brand visual matcher with trained model support.

    On initialization, it tries to load the trained model.
    If the model file doesn't exist, it falls back to keyword matching.

    Usage (SAME AS BEFORE -- no changes needed):
        matcher = BrandVisualMatcher()
        result  = matcher.compare_snapshot(
            screenshot_path = "screenshots/snap_abc123.png",
            final_url       = "https://sbi-login.fakesite.com/login",
            page_title      = "SBI Online Banking",
        )
        print(result.matched_brand)   # "State Bank of India (SBI)"
        print(result.is_spoof)        # True
        print(result.confidence)      # 0.87
    """

    def __init__(self):
        self.model = None
        self.class_names = None
        self.device = None
        self.transform = None
        self.model_loaded = False

        self._try_load_model()

    def _try_load_model(self):
        """Attempts to load the trained model. Falls back silently if not available."""

        if not TORCH_AVAILABLE:
            print("[VisualMatcher] PyTorch not installed -- using keyword fallback.")
            return

        if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
            print("[VisualMatcher] Model not trained yet -- using keyword fallback.")
            print("  Run 'python collect_data.py' then 'python train_model.py' to train.")
            return

        try:
            # Load class labels
            with open(LABELS_PATH, 'r') as f:
                self.class_names = json.load(f)

            num_classes = len(self.class_names)

            # Recreate the model architecture
            model = models.mobilenet_v2(weights=None)
            num_features = model.classifier[1].in_features
            model.classifier = nn.Sequential(
                nn.Dropout(p=0.3),
                nn.Linear(num_features, 256),
                nn.ReLU(),
                nn.Dropout(p=0.2),
                nn.Linear(256, num_classes),
            )

            # Load trained weights
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.load_state_dict(
                torch.load(MODEL_PATH, map_location=self.device, weights_only=True)
            )
            model.eval()
            model.to(self.device)
            self.model = model

            # Preprocessing pipeline (must match training)
            self.transform = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            self.model_loaded = True
            print(f"[VisualMatcher] Model loaded! ({num_classes} classes: {self.class_names})")

        except Exception as e:
            print(f"[VisualMatcher] Failed to load model: {e}")
            print("  Falling back to keyword matching.")
            self.model_loaded = False

    def _predict_brand(self, screenshot_path: str) -> tuple:
        """
        Feeds the screenshot into the neural network.
        Returns (predicted_label, confidence).
        """
        try:
            img = Image.open(screenshot_path).convert("RGB")
            tensor = self.transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probabilities, 1)

            label = self.class_names[predicted_idx.item()]
            conf = confidence.item()

            return label, conf

        except Exception as e:
            print(f"[VisualMatcher] Prediction error: {e}")
            return "unknown", 0.0

    def _keyword_fallback(self, final_url: str, page_title: str) -> tuple:
        """
        Old keyword-based matching as a fallback.
        Returns (predicted_label, confidence).
        """
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

    def _check_domain_legitimacy(self, label: str, final_url: str) -> bool:
        """
        Checks if the URL's domain matches the official domain
        for the detected brand.
        """
        if label == "unknown" or label not in BRAND_DOMAINS:
            return True  # Can't determine, assume legit

        parsed = urlparse(final_url)
        actual_domain = parsed.netloc.lower().lstrip("www.")

        for legit_domain in BRAND_DOMAINS[label]:
            if legit_domain in actual_domain:
                return True

        return False

    def compare_snapshot(
        self,
        screenshot_path: Optional[str],
        final_url: str,
        page_title: str = "",
    ) -> MatchResult:
        """
        Compares the screenshot against known brand templates.

        If the trained model is available, it uses neural network inference.
        Otherwise, it falls back to keyword matching.

        Returns a MatchResult (same structure as before).
        """

        # Decide which method to use
        if self.model_loaded and screenshot_path and os.path.exists(screenshot_path):
            label, confidence = self._predict_brand(screenshot_path)
            method = "model"
        else:
            label, confidence = self._keyword_fallback(final_url, page_title)
            method = "keyword"

        # If predicted as "unknown" or very low confidence, no brand detected
        if label == "unknown" or confidence < 0.3:
            return MatchResult(
                method=method,
                detail=f"No known brand detected (method: {method}).",
            )

        # Get display name
        display_name = BRAND_DISPLAY_NAMES.get(label, label.title())

        # Check if the domain is legit
        domain_legit = self._check_domain_legitimacy(label, final_url)

        # Determine if this is a spoof
        is_spoof = not domain_legit and confidence >= 0.45

        # If domain is legit, reduce the "threat" aspect of the confidence
        effective_confidence = confidence
        if domain_legit:
            effective_confidence = max(confidence - 0.35, 0.1)

        detail = (
            f"Page resembles '{display_name}' with "
            f"{effective_confidence*100:.0f}% confidence "
            f"(method: {method}). "
            f"{'Domain matches official site.' if domain_legit else 'Domain does NOT match official site!'}"
        )

        return MatchResult(
            matched_brand=display_name,
            confidence=round(effective_confidence, 2),
            domain_matches=domain_legit,
            is_spoof=is_spoof,
            detail=detail,
            method=method,
        )


# ---- Quick self-test ---------------------------------------------------------

if __name__ == "__main__":
    matcher = BrandVisualMatcher()

    print(f"\nModel loaded: {matcher.model_loaded}")
    print(f"Method: {'Neural Network' if matcher.model_loaded else 'Keyword Fallback'}\n")

    # Test 1: Fake SBI page
    r1 = matcher.compare_snapshot(
        screenshot_path=None,
        final_url="https://sbi-secure-login.fakesite.com/banking",
        page_title="SBI Online - Secure Login",
    )
    print(f"Test 1 (Fake SBI):  brand={r1.matched_brand}, spoof={r1.is_spoof}, "
          f"conf={r1.confidence}, method={r1.method}")

    # Test 2: Real SBI site
    r2 = matcher.compare_snapshot(
        screenshot_path=None,
        final_url="https://www.onlinesbi.sbi/",
        page_title="State Bank of India",
    )
    print(f"Test 2 (Real SBI):  brand={r2.matched_brand}, spoof={r2.is_spoof}, "
          f"conf={r2.confidence}, method={r2.method}")

    # Test 3: Random site
    r3 = matcher.compare_snapshot(
        screenshot_path=None,
        final_url="https://www.wikipedia.org/",
        page_title="Wikipedia",
    )
    print(f"Test 3 (Wikipedia): brand={r3.matched_brand}, spoof={r3.is_spoof}, "
          f"conf={r3.confidence}, method={r3.method}")
