import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.models.domain import AnomalyDetection, AnomalyObservation

logger = logging.getLogger(__name__)

class AnomalyLLMInterpretationOutput(BaseModel):
    interpretation: str
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    possible_explanations: List[str] = Field(default_factory=list)
    requires_review: bool = False

class AnomalyDetectionLLMResolver:
    """
    Selective Gemini reasoning integration for complex or ambiguous multi-anomaly interpretations.
    Never invents facts or fabricates metrics.
    """

    @classmethod
    def should_invoke_llm(
        cls,
        anomalies: List[AnomalyDetection],
        observations: List[AnomalyObservation]
    ) -> bool:
        """
        Invoked selectively only when:
        1. 2 or more distinct anomalies occur simultaneously
        2. At least one critical severity anomaly occurs
        3. Ambiguous cross-platform price/presence anomaly occurs
        """
        if not anomalies:
            return False
        if len(anomalies) >= 2:
            return True
        if any(a.severity == "critical" for a in anomalies):
            return True
        if any(a.anomaly_type in ["cross_platform_price_anomaly", "platform_presence_anomaly", "provider_data_anomaly"] for a in anomalies):
            return True
        return False

    @classmethod
    async def interpret_anomalies_with_gemini(
        cls,
        product_name: str,
        category: str,
        anomalies: List[AnomalyDetection],
        observations: List[AnomalyObservation],
        platforms: List[str],
        gemini_provider: Optional[Any] = None
    ) -> AnomalyLLMInterpretationOutput:
        """
        Requests structured reasoning from Gemini for ambiguous or multi-anomaly signals.
        """
        # Fallback interpretation if provider is missing
        if not gemini_provider:
            return cls._build_deterministic_fallback(anomalies)

        prompt = (
            f"Analyze the following detected marketplace data anomalies for product '{product_name}' "
            f"(Category: {category}, Platforms: {', '.join(platforms)}).\n"
            f"Verified Anomalies:\n"
        )
        for a in anomalies:
            prompt += (
                f"- Type: {a.anomaly_type}, Severity: {a.severity}, Baseline: {a.baseline}, "
                f"Observed: {a.observed_value}, Deviation: {a.deviation_percent}%\n"
            )

        prompt += (
            "\nProvide a strict JSON response with keys:\n"
            "{\n"
            '  "interpretation": string,\n'
            '  "confidence": float (0.0 to 1.0),\n'
            '  "possible_explanations": list of strings,\n'
            '  "requires_review": boolean\n'
            "}\n"
            "DO NOT fabricate any missing data. Base reasoning strictly on the observed deviations."
        )

        try:
            response_text = await gemini_provider.generate_text(prompt)
            # Clean possible markdown blocks
            clean_json = response_text.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            parsed = json.loads(clean_json)
            return AnomalyLLMInterpretationOutput(
                interpretation=str(parsed.get("interpretation", "")),
                confidence=float(parsed.get("confidence", 0.85)),
                possible_explanations=list(parsed.get("possible_explanations", [])),
                requires_review=bool(parsed.get("requires_review", False))
            )
        except Exception as err:
            logger.warning(f"Gemini anomaly interpretation failed or timed out: {err}. Falling back to deterministic output.")
            return cls._build_deterministic_fallback(anomalies)

    @classmethod
    def _build_deterministic_fallback(
        cls,
        anomalies: List[AnomalyDetection]
    ) -> AnomalyLLMInterpretationOutput:
        if not anomalies:
            return AnomalyLLMInterpretationOutput(
                interpretation="No abnormal activity detected within historical baseline parameters.",
                confidence=0.95,
                possible_explanations=["Normal baseline operation"],
                requires_review=False
            )

        descriptions = []
        explanations = []
        for a in anomalies:
            if a.anomaly_type == "price_spike":
                descriptions.append(f"Price spike (+{a.deviation_percent}%) above historical baseline")
                explanations.append("Observed price is significantly above historical baseline")
            elif a.anomaly_type == "price_crash":
                descriptions.append(f"Price crash ({a.deviation_percent}%) below historical baseline")
                explanations.append("Observed price is significantly below historical baseline")
            elif a.anomaly_type == "unusual_discount":
                descriptions.append(f"Unusually large observed discount ({a.observed_value}%)")
                explanations.append("Observed promotional discount exceeds standard threshold")
            elif a.anomaly_type == "rating_jump":
                descriptions.append(f"Sudden rating jump (+{a.deviation})")
                explanations.append("Rating increased rapidly in recent observation")
            elif a.anomaly_type == "rating_drop":
                descriptions.append(f"Sudden rating drop ({a.deviation})")
                explanations.append("Rating declined rapidly in recent observation")
            elif a.anomaly_type == "review_velocity_spike":
                descriptions.append(f"Review velocity surge (+{a.deviation} reviews)")
                explanations.append("High influx of new reviews recorded")
            elif a.anomaly_type == "cross_platform_price_anomaly":
                descriptions.append(f"Cross-platform price disparity ({a.deviation_percent}%)")
                explanations.append("Verified significant price disparity across active platform listings")
            elif a.anomaly_type == "provider_data_anomaly":
                descriptions.append("Ingestion provider schema out-of-bounds data")
                explanations.append("Provider returned corrupt or invalid data fields")
            else:
                descriptions.append(f"Observed anomaly: {a.anomaly_type}")
                explanations.append(f"Unusual behavior in {a.anomaly_type}")

        return AnomalyLLMInterpretationOutput(
            interpretation="; ".join(descriptions),
            confidence=0.88,
            possible_explanations=explanations,
            requires_review=any(a.severity in ["high", "critical"] for a in anomalies)
        )
