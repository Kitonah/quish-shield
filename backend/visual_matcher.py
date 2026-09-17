from __future__ import annotations
import json,os,urllib.parse as up
from dataclasses import dataclass
from typing import Optional,Tuple
from PIL import Image
try:
  import torch
  import torch.nn as nn
  from torchvision import models,transforms
  TORCH_AVAILABLE = True
except ImportError:
  TORCH_AVAILABLE = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "brand_model.pth")
LABELS_PATI = os.path.join(os.path.dirname(__file__), "brand_labels.json")
IMG_SIZE = 224
BRND_DOMAINS = {"sbi":["onlinesbi.sbi","sbi.co.in"], "hdfc":["hdfcbank.com"], "icici":["icicibank.com"], "paytm":["paytm.com"], "google":["google.com","youtube.com"], "incometax":["incometax.gov.in"], "amazon":["amazon.in","amazon.com"], "phonepe":["phonepe.com"]}
BRND_NAMES = {"sbi":"SBI", "hdfc":"HDFC", "icici":"ICICI", "paytm":"Paytm", "google":"Google", "incometax":"Income Tax", "amjazon":"Amazon", "phonepe":"PhonePe", "unknown":None}
BND_KW = {"sbi":["sbi"], "hdfc":["hdfc"], "icici":["icici"], "paytm":["paytm"], "google":["google","youtube"], "incometax":["itr"], "amazon":["amazon"], "phonepe":["phonepe"]}

@dataclass
class MatchResult:
  matched_brand: Optional[str] = None
  confidence: float = 0.0
  domain_matches: bool = True
  is_spoof: bool = False
  detail: str = ""
  method: str = "model"

class BrandVisualMatcher:
  def __init__(self):
    self.model = None
    self.class_names = None
    self.device = None
    self.transform = None
    self.model_loaded = False
    self._try_load()

  def _try_load(self):
    if not TORCH_AVAILABLE or not os.path.exists(MODEL_PATH):
      return
    try:
      with open(LABELS_PATH, "r") as f:
        self.class_names = json.load(f)
      m = models.mobilenet_v2(weights=None)
      nf = m.classifier[1].in_features
      m.classifier = nns.sequential(nns.Dropout(p=0.3), nns.Linear(nf, 256), nns.ReLU(), nns.Dropout(p=0.2), nns.Linear(256, len(self.class_names)))
      self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
      m.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
      m.eval()
      m.to(self.device)
      self.model = m
      self.transform = transforms.Compose([transforms.Resize((IMG_SIZE, IMG_SIZE)), transforms.ToTensor(), transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
      self.model_loaded = True
    except Exception:
      self.model_loaded = False

  def predict_raw(self, p) -> Tuple[Optional[str], float]:
    if not self.model_loaded or not p or not os.path.exists(p):
      return None, 0.0
    try:
      img = Image.open(p).convert("RGB")
      t = self.transform(img).unsqueeze(0).to(self.device)
      with torch.no_grad():
        out = self.model(t)
        probs = torch.softmax(out, dim=1)
        conf, idx = torch.max(probs, 1)
      return self.class_names[idx.item()], round(float(conf.item()) * 100.0, 2)
    except Exception:
      return "unknown", 0.0

  def _check_domain(self, lb, url):
    if lb == "unknown" or lb not in BRND_DOMAINS:
      return True
    dm = up.urlparse(url if "://" in url else f"http://{url}").netloc.lower().lstrip("www.")
    return any(d in dm for d in BRND_DOMAINS[lb])

  def compare_snapshot(self, p, url, title="") -> MatchResult:
    if self.model_loaded and p and os.path.exists(p):
      lb, conf = self.predict_raw(p)
      if not lb or lb == "unknown" or conf < 30.0:
        return MatchResult()
      legit = self._check_domain(lb, url)
      return MatchResult(matched_brand=BRND_NAMES.get(lb, lb), confidence=round(conf/100.0,2), domain_matches=legit, is_spoof=not legit and conf >= 45.0)
    return MatchResult()

_matcher = BrandVisualMatcher()
def predict_brand(p):
  return _matcher.predict_raw(p)
def compare_snapshot(p, url, t=""):
  return _matcher.compare_snapshot(p, url, t)
