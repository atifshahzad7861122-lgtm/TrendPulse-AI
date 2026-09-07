import json
import time
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from backend.app.core.config import settings
from backend.app.models.domain import (
    UnifiedProduct, ProductPlatformListing, ProductMarketSnapshot, LLMUsageRecord
)
from backend.app.repositories.base import (
    UnifiedProductRepository, MarketplaceProductRepository, LLMUsageRepository
)
from backend.app.services.llm.provider import (
    LLMProvider, LLMRequest, LLMResponse, LLMException, LLMAuthError, LLMRateLimitError, LLMTimeoutError, LLMInvalidResponseError
)
from backend.app.services.llm.providers.mock_provider import MockLLMProvider
from backend.app.services.llm.providers.openai_provider import OpenAIProvider
from backend.app.services.llm.providers.gemini_provider import GeminiProvider
from backend.app.services.llm.providers.anthropic_provider import AnthropicProvider
from backend.app.services.llm.providers.openrouter_provider import OpenRouterProvider
from backend.app.services.llm.providers.groq_provider import GroqLLMProvider, GrokLLMProvider
from backend.app.services.llm.prompts.templates import SYSTEM_PROMPT_CORE, get_prompt_template
from backend.app.services.llm.context_builder import ContextBuilder
from backend.app.services.llm.cache import llm_cache, LLMResponseCache
from backend.app.schemas.llm import (
    AIProductAnalysisResponse, AIProductSummaryResponse, AICategoryAnalysisResponse,
    AIMarketComparisonResponse, AITrendAnalysisResponse, DataFreshnessMeta
)

class LLMService:
    """
    High-level orchestrator for TrendPulse AI LLM Intelligence operations.
    Coordinates context building, prompt execution, output repair, usage tracking, and caching.
    """

    def __init__(
        self,
        unified_repo: UnifiedProductRepository,
        marketplace_repo: MarketplaceProductRepository,
        usage_repo: LLMUsageRepository,
        provider: Optional[LLMProvider] = None
    ):
        self.unified_repo = unified_repo
        self.marketplace_repo = marketplace_repo
        self.usage_repo = usage_repo
        self.provider = provider or self._init_provider()

    def _init_provider(self) -> LLMProvider:
        """Factory initializing the configured provider from application settings."""
        p_name = (settings.LLM_PROVIDER or "mock").lower()
        key = settings.LLM_API_KEY
        model = settings.LLM_MODEL
        base_url = settings.LLM_BASE_URL

        if p_name == "openai":
            return OpenAIProvider(api_key=key, model=model, base_url=base_url)
        elif p_name == "groq":
            return GroqLLMProvider(api_key=settings.GROQ_API_KEY or key, model=model or "llama-3.3-70b-versatile", base_url=base_url)
        elif p_name in ["grok", "xai"]:
            return GrokLLMProvider(api_key=key or settings.XAI_API_KEY or settings.GROK_API_KEY or settings.GROQ_API_KEY, model=model or "grok-beta", base_url=base_url)
        elif p_name == "gemini":
            gemini_model = model if (model and "gemini" in model.lower()) else "gemini-1.5-flash"
            return GeminiProvider(api_key=key, model=gemini_model, base_url=base_url)

        elif p_name == "anthropic":
            return AnthropicProvider(api_key=key, model=model or "claude-3-5-sonnet-20241022", base_url=base_url)
        elif p_name == "openrouter":
            return OpenRouterProvider(api_key=key, model=model or "deepseek/deepseek-chat", base_url=base_url)
        else:
            return MockLLMProvider(api_key=key or "mock-key", model=model or "mock-model-v1", base_url=base_url)

    def _execute_with_retry(self, request: LLMRequest, max_retries: int = 3) -> LLMResponse:
        """Executes LLM request with exponential backoff on transient errors."""
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.provider.generate(request)
            except LLMAuthError:
                # Permanent credential failure - DO NOT retry
                raise
            except (LLMRateLimitError, LLMTimeoutError, LLMException) as e:
                last_exception = e
                if attempt < max_retries:
                    sleep_time = (2 ** (attempt - 1)) * 0.5
                    time.sleep(sleep_time)
                else:
                    raise last_exception
        raise last_exception or LLMException("LLM request failed after retries.")

    def _repair_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Attempts multiple robust JSON extraction and repair strategies."""
        text = raw_text.strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Strip markdown fences
        if "```" in text:
            extracted = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if extracted:
                try:
                    return json.loads(extracted[0].strip())
                except Exception:
                    pass

        # Extract outermost JSON brackets
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        raise LLMInvalidResponseError("Unable to repair or parse valid JSON from LLM output.")

    def _record_telemetry(
        self,
        request_type: str,
        prompt_version: str,
        resp: Optional[LLMResponse],
        status: str,
        user_id: Optional[str],
        workspace_id: Optional[str],
        error_code: Optional[int] = None,
        latency_ms: float = 0.0
    ) -> None:
        """Records an immutable usage tracking record."""
        record = LLMUsageRecord(
            id=f"llm_use_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            workspace_id=workspace_id,
            provider=resp.provider if resp else (settings.LLM_PROVIDER or "unknown"),
            model=resp.model if resp else (settings.LLM_MODEL or "unknown"),
            request_type=request_type,
            prompt_version=prompt_version,
            input_tokens=resp.input_tokens if resp else 0,
            output_tokens=resp.output_tokens if resp else 0,
            total_tokens=resp.total_tokens if resp else 0,
            estimated_cost=resp.estimated_cost if resp else 0.0,
            latency_ms=resp.latency_ms if resp else latency_ms,
            status=status,
            error_code=error_code,
            created_at=datetime.now(timezone.utc)
        )
        self.usage_repo.record_usage(record)

    # -------------------------------------------------------------------------
    # 1. Product Analysis
    # -------------------------------------------------------------------------
    def analyze_product(
        self,
        unified_product_id: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> AIProductAnalysisResponse:
        product = self.unified_repo.get_unified_product(unified_product_id)
        if not product:
            raise KeyError(f"Unified product '{unified_product_id}' not found.")


        listings = self.unified_repo.list_listings_for_product(unified_product_id)
        # Fetch snapshot history if available
        history: List[ProductMarketSnapshot] = []
        for l in listings:
            h = self.marketplace_repo.get_snapshots(platform=l.platform, product_id=l.platform_product_id, limit=10)
            history.extend(h)


        prompt_version = "product_analysis_v1"
        data_fingerprint = f"{product.updated_at.isoformat()}::{len(listings)}::{len(history)}"
        cache_key = LLMResponseCache.generate_key(
            unified_product_id, "product_analysis", prompt_version, data_fingerprint, self.provider.model
        )

        if not force_refresh and settings.LLM_CACHE_ENABLED:
            cached_data = llm_cache.get(cache_key)
            if cached_data:
                self._record_telemetry("product_analysis", prompt_version, None, "cached", user_id, workspace_id)
                res = AIProductAnalysisResponse(**cached_data)
                res.is_cached = True
                return res

        context = ContextBuilder.build_product_context(product, listings, history)
        prompt_tmpl = get_prompt_template(prompt_version)
        prompt = prompt_tmpl.format(
            context_json=json.dumps(context, indent=2),
            category=product.category or "General"
        )

        req = LLMRequest(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CORE,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            json_mode=True
        )

        start_time = time.perf_counter()
        try:
            resp = self._execute_with_retry(req)
            parsed = resp.parsed_json or self._repair_and_parse_json(resp.content)
            self._record_telemetry("product_analysis", prompt_version, resp, "success", user_id, workspace_id)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500)
            self._record_telemetry("product_analysis", prompt_version, None, "failed", user_id, workspace_id, status_code, elapsed)
            raise

        freshness = ContextBuilder.calculate_data_freshness(listings)
        analysis_resp = AIProductAnalysisResponse(
            unified_product_id=product.unified_product_id,
            canonical_name=product.canonical_name,
            summary=parsed.get("summary", "Analysis completed."),
            category=parsed.get("category", product.category),
            confidence_score=float(parsed.get("confidence_score", 0.9)),
            key_signals=parsed.get("key_signals", []),
            opportunities=parsed.get("opportunities", []),
            risks=parsed.get("risks", []),
            recommendations=parsed.get("recommendations", []),
            pricing_analysis=parsed.get("pricing_analysis", {}),
            data_freshness=freshness,
            is_cached=False,
            prompt_version=prompt_version,
            provider=resp.provider,
            model=resp.model,
            tokens_used=resp.total_tokens,
            latency_ms=resp.latency_ms
        )

        if settings.LLM_CACHE_ENABLED:
            llm_cache.set(cache_key, analysis_resp.model_dump(), ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)

        return analysis_resp

    # -------------------------------------------------------------------------
    # 2. Product Summary
    # -------------------------------------------------------------------------
    def summarize_product(
        self,
        unified_product_id: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> AIProductSummaryResponse:
        product = self.unified_repo.get_unified_product(unified_product_id)
        if not product:
            raise KeyError(f"Unified product '{unified_product_id}' not found.")

        listings = self.unified_repo.list_listings_for_product(unified_product_id)
        prompt_version = "product_summary_v1"
        data_fingerprint = f"{product.updated_at.isoformat()}::{len(listings)}"
        cache_key = LLMResponseCache.generate_key(
            unified_product_id, "product_summary", prompt_version, data_fingerprint, self.provider.model
        )

        if not force_refresh and settings.LLM_CACHE_ENABLED:
            cached_data = llm_cache.get(cache_key)
            if cached_data:
                self._record_telemetry("product_summary", prompt_version, None, "cached", user_id, workspace_id)
                res = AIProductSummaryResponse(**cached_data)
                res.is_cached = True
                return res

        context = ContextBuilder.build_product_context(product, listings)
        prompt = get_prompt_template(prompt_version).format(
            context_json=json.dumps(context, indent=2)
        )

        req = LLMRequest(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CORE,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            json_mode=True
        )

        start_time = time.perf_counter()
        try:
            resp = self._execute_with_retry(req)
            parsed = resp.parsed_json or self._repair_and_parse_json(resp.content)
            self._record_telemetry("product_summary", prompt_version, resp, "success", user_id, workspace_id)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500)
            self._record_telemetry("product_summary", prompt_version, None, "failed", user_id, workspace_id, status_code, elapsed)
            raise

        freshness = ContextBuilder.calculate_data_freshness(listings)
        summary_resp = AIProductSummaryResponse(
            unified_product_id=product.unified_product_id,
            canonical_name=product.canonical_name,
            executive_summary=parsed.get("executive_summary", "Summary generated."),
            key_takeaways=parsed.get("key_takeaways", []),
            target_audience=parsed.get("target_audience"),
            competitive_edge=parsed.get("competitive_edge"),
            data_freshness=freshness,
            is_cached=False,
            prompt_version=prompt_version,
            provider=resp.provider,
            model=resp.model,
            tokens_used=resp.total_tokens,
            latency_ms=resp.latency_ms
        )

        if settings.LLM_CACHE_ENABLED:
            llm_cache.set(cache_key, summary_resp.model_dump(), ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)

        return summary_resp

    # -------------------------------------------------------------------------
    # 3. Market Comparison
    # -------------------------------------------------------------------------
    def compare_market(
        self,
        unified_product_id: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> AIMarketComparisonResponse:
        product = self.unified_repo.get_unified_product(unified_product_id)
        if not product:
            raise KeyError(f"Unified product '{unified_product_id}' not found.")

        listings = self.unified_repo.list_listings_for_product(unified_product_id)
        prompt_version = "market_comparison_v1"
        data_fingerprint = f"{product.updated_at.isoformat()}::{len(listings)}"
        cache_key = LLMResponseCache.generate_key(
            unified_product_id, "market_comparison", prompt_version, data_fingerprint, self.provider.model
        )

        if not force_refresh and settings.LLM_CACHE_ENABLED:
            cached_data = llm_cache.get(cache_key)
            if cached_data:
                self._record_telemetry("market_comparison", prompt_version, None, "cached", user_id, workspace_id)
                res = AIMarketComparisonResponse(**cached_data)
                res.is_cached = True
                return res

        context = ContextBuilder.build_product_context(product, listings)
        prompt = get_prompt_template(prompt_version).format(
            context_json=json.dumps(context, indent=2)
        )

        req = LLMRequest(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CORE,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            json_mode=True
        )

        start_time = time.perf_counter()
        try:
            resp = self._execute_with_retry(req)
            parsed = resp.parsed_json or self._repair_and_parse_json(resp.content)
            self._record_telemetry("market_comparison", prompt_version, resp, "success", user_id, workspace_id)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500)
            self._record_telemetry("market_comparison", prompt_version, None, "failed", user_id, workspace_id, status_code, elapsed)
            raise

        freshness = ContextBuilder.calculate_data_freshness(listings)
        comp_resp = AIMarketComparisonResponse(
            unified_product_id=product.unified_product_id,
            canonical_name=product.canonical_name,
            cross_platform_overview=parsed.get("cross_platform_overview", "Comparison complete."),
            price_arbitrage_analysis=parsed.get("price_arbitrage_analysis", "No arbitrage identified."),
            seller_and_vendor_landscape=parsed.get("seller_and_vendor_landscape", "Sellers analyzed."),
            platform_comparison_breakdown=parsed.get("platform_comparison_breakdown", []),
            recommendations=parsed.get("recommendations", []),
            data_freshness=freshness,
            is_cached=False,
            prompt_version=prompt_version,
            provider=resp.provider,
            model=resp.model,
            tokens_used=resp.total_tokens,
            latency_ms=resp.latency_ms
        )

        if settings.LLM_CACHE_ENABLED:
            llm_cache.set(cache_key, comp_resp.model_dump(), ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)

        return comp_resp

    # -------------------------------------------------------------------------
    # 4. Trend Analysis
    # -------------------------------------------------------------------------
    def analyze_trend(
        self,
        unified_product_id: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> AITrendAnalysisResponse:
        product = self.unified_repo.get_unified_product(unified_product_id)
        if not product:
            raise KeyError(f"Unified product '{unified_product_id}' not found.")

        listings = self.unified_repo.list_listings_for_product(unified_product_id)
        history: List[ProductMarketSnapshot] = []
        for l in listings:
            h = self.marketplace_repo.get_snapshots(platform=l.platform, product_id=l.platform_product_id, limit=10)
            history.extend(h)


        prompt_version = "trend_analysis_v1"
        data_fingerprint = f"{product.updated_at.isoformat()}::{len(history)}"
        cache_key = LLMResponseCache.generate_key(
            unified_product_id, "trend_analysis", prompt_version, data_fingerprint, self.provider.model
        )

        if not force_refresh and settings.LLM_CACHE_ENABLED:
            cached_data = llm_cache.get(cache_key)
            if cached_data:
                self._record_telemetry("trend_analysis", prompt_version, None, "cached", user_id, workspace_id)
                res = AITrendAnalysisResponse(**cached_data)
                res.is_cached = True
                return res

        context = ContextBuilder.build_product_context(product, listings, history)
        prompt = get_prompt_template(prompt_version).format(
            context_json=json.dumps(context, indent=2)
        )

        req = LLMRequest(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CORE,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            json_mode=True
        )

        start_time = time.perf_counter()
        try:
            resp = self._execute_with_retry(req)
            parsed = resp.parsed_json or self._repair_and_parse_json(resp.content)
            self._record_telemetry("trend_analysis", prompt_version, resp, "success", user_id, workspace_id)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500)
            self._record_telemetry("trend_analysis", prompt_version, None, "failed", user_id, workspace_id, status_code, elapsed)
            raise

        freshness = ContextBuilder.calculate_data_freshness(listings)
        trend_resp = AITrendAnalysisResponse(
            unified_product_id=product.unified_product_id,
            canonical_name=product.canonical_name,
            trend_trajectory=parsed.get("trend_trajectory", "Stable Growth"),
            velocity_assessment=parsed.get("velocity_assessment", "Stable velocity."),
            volatility_risk=parsed.get("volatility_risk", "Low"),
            historical_price_action=parsed.get("historical_price_action", "Price remained stable."),
            predictive_outlook_30d=parsed.get("predictive_outlook_30d", "Positive outlook."),
            data_freshness=freshness,
            is_cached=False,
            prompt_version=prompt_version,
            provider=resp.provider,
            model=resp.model,
            tokens_used=resp.total_tokens,
            latency_ms=resp.latency_ms
        )

        if settings.LLM_CACHE_ENABLED:
            llm_cache.set(cache_key, trend_resp.model_dump(), ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)

        return trend_resp

    # -------------------------------------------------------------------------
    # 5. Category Analysis
    # -------------------------------------------------------------------------
    def analyze_category(
        self,
        category: str,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> AICategoryAnalysisResponse:
        all_products = self.unified_repo.list_unified_products(category=category, limit=20)
        if not all_products:
            # Fallback to all products if category is empty
            all_products = self.unified_repo.list_unified_products(limit=20)


        pairs = []
        for p in all_products:
            lists = self.unified_repo.list_listings_for_product(p.unified_product_id)
            pairs.append((p, lists))

        prompt_version = "category_analysis_v1"
        data_fingerprint = f"{category}::{len(all_products)}"
        cache_key = LLMResponseCache.generate_key(
            category, "category_analysis", prompt_version, data_fingerprint, self.provider.model
        )

        if not force_refresh and settings.LLM_CACHE_ENABLED:
            cached_data = llm_cache.get(cache_key)
            if cached_data:
                self._record_telemetry("category_analysis", prompt_version, None, "cached", user_id, workspace_id)
                res = AICategoryAnalysisResponse(**cached_data)
                res.is_cached = True
                return res

        context = ContextBuilder.build_category_context(category, pairs)
        prompt = get_prompt_template(prompt_version).format(
            context_json=json.dumps(context, indent=2),
            category=category
        )

        req = LLMRequest(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_CORE,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            json_mode=True
        )

        start_time = time.perf_counter()
        try:
            resp = self._execute_with_retry(req)
            parsed = resp.parsed_json or self._repair_and_parse_json(resp.content)
            self._record_telemetry("category_analysis", prompt_version, resp, "success", user_id, workspace_id)
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = getattr(e, "status_code", 500)
            self._record_telemetry("category_analysis", prompt_version, None, "failed", user_id, workspace_id, status_code, elapsed)
            raise

        all_listings_flat = [l for _, lists in pairs for l in lists]
        freshness = ContextBuilder.calculate_data_freshness(all_listings_flat)

        cat_resp = AICategoryAnalysisResponse(
            category=category,
            market_overview=parsed.get("market_overview", "Category evaluated."),
            demand_state=parsed.get("demand_state", "High Steady Demand"),
            price_range_summary=parsed.get("price_range_summary", "Prices evaluated across sample."),
            growth_drivers=parsed.get("growth_drivers", []),
            threats_and_challenges=parsed.get("threats_and_challenges", []),
            strategic_advice=parsed.get("strategic_advice", []),
            data_freshness=freshness,
            is_cached=False,
            prompt_version=prompt_version,
            provider=resp.provider,
            model=resp.model,
            tokens_used=resp.total_tokens,
            latency_ms=resp.latency_ms
        )

        if settings.LLM_CACHE_ENABLED:
            llm_cache.set(cache_key, cat_resp.model_dump(), ttl_seconds=settings.LLM_CACHE_TTL_SECONDS)

        return cat_resp
