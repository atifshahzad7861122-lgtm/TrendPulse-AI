import json
import logging
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TrendLLMInterpretationOutput(BaseModel):
    interpretation: str
    confidence: float = 0.85
    supporting_signals: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    requires_review: bool = False

class TrendDetectionLLMResolver:
    """
    Selective Gemini reasoning service for Agent 4.
    Invoked ONLY for complex multi-signal contextual analysis or ambiguous contradictions.
    Never invents missing measurements.
    """

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    def interpret_complex_trend(
        self,
        product_info: Dict[str, Any],
        observed_signals: List[Dict[str, Any]],
        freshness: str
    ) -> Tuple[TrendLLMInterpretationOutput, bool]:
        """
        Queries Gemini for contextual interpretation of multi-signal trends.
        Returns: (TrendLLMInterpretationOutput, success_boolean)
        """
        # If no client or no signals, return default fallback
        if not self.gemini_client:
            return self._default_fallback("Gemini client not initialized"), False

        system_instruction = (
            "You are the AI Trend Intelligence Arbiter for TrendPulse AI.\n"
            "Analyze the provided observed product metrics and deterministic trend signals.\n"
            "Provide a grounded, objective contextual explanation.\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. NEVER invent sales numbers, profit figures, or metrics not present in input.\n"
            "2. Ground every conclusion strictly in the provided observations.\n"
            "3. Output MUST be valid JSON conforming to the requested schema."
        )

        prompt_payload = {
            "task": "interpret_marketplace_trend_signals",
            "product": {
                "name": product_info.get("canonical_name", "Unknown"),
                "brand": product_info.get("brand", "Unknown"),
                "category": product_info.get("category", "Unknown"),
                "platforms": product_info.get("platforms", [])
            },
            "data_freshness": freshness,
            "observed_signals": observed_signals
        }

        user_content = json.dumps(prompt_payload, indent=2)

        try:
            if hasattr(self.gemini_client, "generate_structured_json") and not hasattr(self.gemini_client, "generate_content"):
                data = self.gemini_client.generate_structured_json(
                    prompt=user_content,
                    system_instruction=system_instruction,
                    schema=TrendLLMInterpretationOutput
                )
                if isinstance(data, dict):
                    output = TrendLLMInterpretationOutput(**data)
                    return output, True
                elif isinstance(data, TrendLLMInterpretationOutput):
                    return data, True
                else:
                    return self._default_fallback("Unexpected schema format"), False
            elif hasattr(self.gemini_client, "generate_content"):
                resp = self.gemini_client.generate_content(
                    prompt=f"{system_instruction}\n\nInput:\n{user_content}\n\nRespond with JSON:"
                )
                raw_text = getattr(resp, "text", str(resp))
                cleaned = self._clean_json_markdown(raw_text)
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return TrendLLMInterpretationOutput(**parsed), True
                return self._default_fallback("Non-dict JSON"), False
            else:
                return self._default_fallback("Unsupported Gemini client method"), False

        except json.JSONDecodeError as jde:
            logger.warning(f"Gemini returned invalid JSON for trend interpretation: {jde}")
            return self._default_fallback("Failed to parse Gemini JSON response"), False
        except Exception as e:
            logger.error(f"Gemini trend interpretation error: {e}")
            return self._default_fallback(f"Gemini error: {str(e)}"), False

    @staticmethod
    def _clean_json_markdown(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @staticmethod
    def _default_fallback(reason: str) -> TrendLLMInterpretationOutput:
        return TrendLLMInterpretationOutput(
            interpretation=f"Deterministic signal analysis maintained ({reason}).",
            confidence=0.80,
            supporting_signals=[],
            contradictions=[],
            requires_review=False
        )
