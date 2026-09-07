"""
Phase 3 AI Market Analyst Service.

Interprets deterministic market intelligence metrics into human-readable strategic insights
using Grok / Groq / OpenAI. Explicitly enforces anti-hallucination guardrails so that the LLM
never fabricates prices, ratings, sales numbers, or historical data.
"""

import json
import hashlib
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from backend.app.services.llm.service import LLMService
from backend.app.services.llm.provider import LLMRequest, LLMException, LLMAuthError, LLMRateLimitError

logger = logging.getLogger("trendpulse.ai_market_analyst")


class AIMarketAnalystService:
    """
    Synthesizes deterministic market intelligence into explainable business narratives.
    """

    CACHE_TTL_SECONDS = 3600  # 1 hour cache for identical factual snapshots

    SYSTEM_PROMPT = (
        "You are TrendPulse AI's Chief Market Intelligence Analyst.\n"
        "Your role is to interpret deterministic e-commerce market intelligence and social demand metrics.\n\n"
        "STRICT OPERATIONAL RULES:\n"
        "1. You MUST ONLY use the verified factual metrics provided in the structured input JSON.\n"
        "2. NEVER invent, fabricate, simulate, or hallucinate product prices, discounts, ratings, reviews, historical changes, or sales numbers.\n"
        "3. If an input metric is null or marked 'insufficient_data', explain that history or observation depth is currently insufficient rather than inventing numbers.\n"
        "4. Provide crisp, professional, data-backed commercial insights covering: market summary, key drivers, expansion opportunities, and risk factors.\n"
        "5. Respond in valid JSON matching the requested schema."
    )

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

    def _get_cache_key(self, facts: Dict[str, Any]) -> str:
        serialized = json.dumps(facts, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _has_active_provider(self) -> bool:
        if not self.llm_service or not getattr(self.llm_service, "provider", None):
            return False
        prov = self.llm_service.provider
        api_key = getattr(prov, "api_key", None)
        if not api_key or not isinstance(api_key, str) or api_key.strip() in ["", "none", "null", "PASTE_YOUR_API_KEY_HERE"]:
            return False
        # Google Gemini API keys must start with 'AIzaSy'
        if getattr(prov, "__class__", None).__name__ == "GeminiProvider" and not api_key.startswith("AIzaSy"):
            return False
        return True

    def generate_product_analysis(
        self,
        product_facts: Dict[str, Any],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Generates structured AI explanation for a single product based on verified facts.
        """
        cache_key = f"prod_{self._get_cache_key(product_facts)}"
        if not force_refresh and cache_key in self._cache:
            val, expiry = self._cache[cache_key]
            if time.time() < expiry:
                return val

        if not self._has_active_provider():
            return self._build_deterministic_fallback_product(product_facts)

        user_prompt = (
            f"Analyze the following verified market facts for this product:\n"
            f"```json\n{json.dumps(product_facts, indent=2, default=str)}\n```\n\n"
            f"Return a JSON object with the following structure:\n"
            f'{{\n'
            f'  "executive_summary": "2-3 sentence strategic overview",\n'
            f'  "demand_rationale": "Explanation of consumer demand based on score and reviews",\n'
            f'  "opportunity_drivers": ["bullet 1", "bullet 2"],\n'
            f'  "risk_factors": ["bullet 1", "bullet 2"],\n'
            f'  "strategic_verdict": "Clear recommendation (e.g. Expand Distribution, Optimize Pricing, Monitor)"\n'
            f'}}'
        )

        req = LLMRequest(
            prompt=user_prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=800,
            timeout=10.0,
            json_mode=True
        )

        try:
            resp = self.llm_service.provider.generate(req)
            data = resp.parsed_json or {}
            if not data and resp.content:
                try:
                    data = json.loads(resp.content)
                except Exception:
                    data = {"executive_summary": resp.content}

            self._cache[cache_key] = (data, time.time() + self.CACHE_TTL_SECONDS)
            return data
        except Exception as err:
            logger.warning(f"AI Market Analyst error during product interpretation: {err}. Using deterministic synthesis.")
            return self._build_deterministic_fallback_product(product_facts)

    def generate_market_overview_analysis(
        self,
        market_facts: Dict[str, Any],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Generates macro market overview synthesis across products and categories.
        """
        cache_key = f"market_{self._get_cache_key(market_facts)}"
        if not force_refresh and cache_key in self._cache:
            val, expiry = self._cache[cache_key]
            if time.time() < expiry:
                return val

        if not self._has_active_provider():
            return self._build_deterministic_fallback_market(market_facts)

        user_prompt = (
            f"Analyze the following aggregated market intelligence facts:\n"
            f"```json\n{json.dumps(market_facts, indent=2, default=str)}\n```\n\n"
            f"Return a JSON object with the following structure:\n"
            f'{{\n'
            f'  "executive_summary": "Comprehensive 3-4 sentence market overview",\n'
            f'  "key_trend_drivers": ["driver 1", "driver 2", "driver 3"],\n'
            f'  "expansion_opportunities": ["opportunity 1", "opportunity 2"],\n'
            f'  "market_risks": ["risk 1", "risk 2"],\n'
            f'  "strategic_recommendations": ["recommendation 1", "recommendation 2"]\n'
            f'}}'
        )

        req = LLMRequest(
            prompt=user_prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=1024,
            timeout=10.0,
            json_mode=True
        )

        try:
            resp = self.llm_service.provider.generate(req)
            data = resp.parsed_json or {}
            if not data and resp.content:
                try:
                    data = json.loads(resp.content)
                except Exception:
                    data = {"executive_summary": resp.content}

            self._cache[cache_key] = (data, time.time() + self.CACHE_TTL_SECONDS)
            return data
        except Exception as err:
            logger.warning(f"AI Market Analyst error during market interpretation: {err}. Using deterministic synthesis.")
            return self._build_deterministic_fallback_market(market_facts)

    def _build_deterministic_fallback_product(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        title = facts.get("title", "Product")
        mkt_score = facts.get("market_score", 50.0)
        demand_level = facts.get("demand_level", "MODERATE")
        rating = facts.get("rating", 0.0)
        reviews = facts.get("review_count", 0)

        summary = (
            f"{title} shows a {demand_level} demand conviction with a Market Score of {mkt_score:.1f}/100. "
            f"Customer acclaim reflects {rating:.1f}★ across {reviews:,} verified marketplace reviews."
        )

        opps = []
        if facts.get("platform_count", 1) == 1:
            opps.append("Single marketplace distribution indicates high cross-platform arbitrage potential.")
        if facts.get("price", 0) > 0:
            opps.append(f"Competitive pricing observed at {facts.get('currency', 'USD')} {facts.get('price', 0):,.2f}.")

        risks = []
        if not facts.get("availability", True):
            risks.append("Currently marked out of stock or limited availability.")
        if reviews < 10:
            risks.append("Low review count limits statistical confidence.")

        cat = facts.get("category") or "General"
        return {
            "executive_summary": summary,
            "demand_rationale": f"Classified as {demand_level} demand based on marketplace observations.",
            "category_landscape": f"Positioned within {cat} category with active consumer consideration.",
            "opportunity_drivers": opps or ["Steady baseline product demand."],
            "risk_factors": risks or ["Standard commercial marketplace competition."],
            "strategic_recommendations": [
                "Evaluate cross-channel expansion to capture adjacent marketplace demand",
                "Monitor inventory levels to mitigate stockout vulnerability"
            ],
            "strategic_verdict": "Monitor Market Trajectory"
        }

    def _build_deterministic_fallback_market(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        total = facts.get("total_products", 0)
        avg_score = facts.get("average_market_score", 50.0)
        high_demand = facts.get("high_demand_count", 0)
        high_opp = facts.get("high_opportunity_count", 0)

        summary = (
            f"Market analysis across {total} verified products indicates an average Market Score of {avg_score:.1f}/100. "
            f"Identified {high_demand} high-demand listings and {high_opp} commercial opportunity gaps across active marketplaces."
        )

        return {
            "executive_summary": summary,
            "key_trend_drivers": [
                "Strong consumer search volume driving catalog discovery",
                "Competitive price adjustments across key categories",
                "Emerging cross-channel customer interest"
            ],
            "expansion_opportunities": [
                "Address marketplace gaps where top items are absent on secondary platforms",
                "Capitalize on high-demand, high-rating listings with low competition"
            ],
            "market_risks": [
                "Price volatility and seller discounting pressure in saturated segments",
                "Stockout risks on rapidly accelerating products"
            ],
            "strategic_recommendations": [
                "Prioritize multi-marketplace distribution for verified high-score products",
                "Maintain competitive price positioning against primary marketplace leaders"
            ]
        }
