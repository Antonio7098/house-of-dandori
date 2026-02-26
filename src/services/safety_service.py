"""Perspective API powered safety checks for prompts and model outputs."""
from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

try:  # Optional dependency during local dev
    from googleapiclient import discovery
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - handled gracefully at runtime
    discovery = None  # type: ignore
    HttpError = Exception  # type: ignore

SafetyStage = Literal["prompt", "output"]
DEFAULT_ATTRIBUTES = ["TOXICITY", "IDENTITY_ATTACK", "SEXUALLY_EXPLICIT", "PROFANITY"]
FALLBACK_KEYWORDS = {
    "TOXICITY": ["kill", "murder", "genocide", "violence", "racist"],
    "IDENTITY_ATTACK": ["slur", "white trash", "inferior race", "hate women", "hate men"],
    "SEXUALLY_EXPLICIT": ["nsfw", "porn", "explicit", "sexual act", "nude"],
    "PROFANITY": ["damn", "shit", "fuck"]
}
PROMPT_BLOCK_MESSAGE = "Prompt blocked by safety system."
OUTPUT_BLOCK_MESSAGE = "Model response blocked by safety system."


@dataclass
class SafetyResult:
    safe: bool
    scores: Dict[str, float]
    reasons: List[str]
    stage: SafetyStage
    source: str
    message: Optional[str] = None


class SafetyService:
    def __init__(self):
        base_dir = Path(__file__).resolve().parents[2]
        self.api_key = os.environ.get("PERSPECTIVE_API_KEY")
        self.attributes = DEFAULT_ATTRIBUTES
        self.threshold_path = Path(
            os.environ.get("SAFETY_THRESHOLDS_PATH", base_dir / "assets" / "safety_thresholds.json")
        )
        self.log_dir = Path(os.environ.get("SAFETY_LOG_DIR", base_dir / "logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "safety.log"
        self._client = None
        self._threshold_cache: Optional[Dict[str, Dict[str, float]]] = None
        self._client_lock = threading.Lock()

    # -------------------- Public API --------------------
    def check_prompt(self, text: str) -> SafetyResult:
        return self._evaluate(text, stage="prompt", block_message=PROMPT_BLOCK_MESSAGE)

    def check_output(self, text: str) -> SafetyResult:
        return self._evaluate(text, stage="output", block_message=OUTPUT_BLOCK_MESSAGE)

    def log_block(self, *, stage: SafetyStage, text: str, result: SafetyResult) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "reasons": result.reasons,
            "scores": result.scores,
            "source": result.source,
            "excerpt": text[:200],
        }
        try:
            with self.log_file.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Logging failures should not break the request

    # -------------------- Internal helpers --------------------
    def _evaluate(self, text: str, *, stage: SafetyStage, block_message: str) -> SafetyResult:
        text = (text or "").strip()
        if not text:
            return SafetyResult(True, {}, [], stage, "empty", None)

        report, source = self._run_analysis(text)
        thresholds = self._get_thresholds(stage)
        reasons = self._flag_reasons(report, thresholds)
        safe = not reasons
        message = None
        if not safe:
            message = block_message + " " + " | ".join(reasons)
        return SafetyResult(safe, report, reasons, stage, source, message)

    def _run_analysis(self, text: str) -> Tuple[Dict[str, float], str]:
        client = self._get_client()
        if not client:
            return self._fallback_report(text), "fallback"

        try:
            body = {
                "comment": {"text": text},
                "requestedAttributes": {attr: {} for attr in self.attributes},
            }
            response = (
                client.comments()  # type: ignore[attr-defined]
                .analyze(body=body)
                .execute()
            )
            return self._parse_scores(response), "perspective"
        except HttpError:
            return self._fallback_report(text), "fallback"
        except Exception:
            return self._fallback_report(text), "fallback"

    def _parse_scores(self, response: Dict[str, any]) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        attribute_scores = response.get("attributeScores") or {}
        for attr, payload in attribute_scores.items():
            summary = payload.get("summaryScore", {}).get("value")
            if summary is not None:
                scores[attr.upper()] = float(summary)
                continue
            spans = payload.get("spanScores") or []
            if spans:
                scores[attr.upper()] = float(spans[0].get("score", {}).get("value", 0.0))
        return scores

    def _fallback_report(self, text: str) -> Dict[str, float]:
        lowered = text.lower()
        report: Dict[str, float] = {}
        for attr, keywords in FALLBACK_KEYWORDS.items():
            for keyword in keywords:
                pattern = r"\b{}\b".format(re.escape(keyword.lower()))
                if re.search(pattern, lowered):
                    report[attr] = 1.0
                    break
        return report

    def _flag_reasons(self, report: Dict[str, float], thresholds: Dict[str, float]) -> List[str]:
        reasons: List[str] = []
        for attr, score in report.items():
            limit = thresholds.get(attr.upper(), 1.0)
            if score >= limit:
                reasons.append(f"{attr.upper()} {score:.2f} ≥ {limit:.2f}")
        return reasons

    def _get_thresholds(self, stage: SafetyStage) -> Dict[str, float]:
        if self._threshold_cache is None:
            self._threshold_cache = self._load_thresholds()
        key = "INPUT" if stage == "prompt" else "OUTPUT"
        return self._threshold_cache.get(key, {})

    def _load_thresholds(self) -> Dict[str, Dict[str, float]]:
        if not self.threshold_path.exists():
            return {"INPUT": {}, "OUTPUT": {}}
        try:
            with self.threshold_path.open("r", encoding="utf-8") as fp:
                raw = json.load(fp)
            return {
                "INPUT": {k.upper(): float(v) for k, v in (raw.get("INPUT") or {}).items()},
                "OUTPUT": {k.upper(): float(v) for k, v in (raw.get("OUTPUT") or {}).items()},
            }
        except Exception:
            return {"INPUT": {}, "OUTPUT": {}}

    def _get_client(self):
        if not self.api_key or discovery is None:
            return None
        if self._client:
            return self._client
        with self._client_lock:
            if self._client:
                return self._client
            self._client = discovery.build(
                "commentanalyzer",
                "v1alpha1",
                developerKey=self.api_key,
                discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
                cache_discovery=False,
            )
            return self._client


safety_service = SafetyService()
