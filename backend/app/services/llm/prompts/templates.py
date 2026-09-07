from typing import Dict, Any

SYSTEM_PROMPT_CORE = """You are TrendPulse AI's Principal E-Commerce Market Intelligence Engine.
You synthesize and analyze verified multi-platform marketplace data (Daraz Pakistan, Shopify DTC, and connected global commerce feeds).

CRITICAL GROUNDING & ANTI-FABRICATION CONSTRAINTS:
1. Ground every conclusion strictly and exclusively on the verified structured data provided in the prompt.
2. NEVER invent, fabricate, extrapolate, or hallucinate missing data points (such as unobserved sales volume, fake revenues, estimated unit counts, fake inventory quantities, or fictional competitor rankings).
3. If an indicator or metric is missing, explicitly state "Data unavailable" or return null. Never guess.
4. Distinguish clearly between Live data and Cached historical observations based on the data_status and data_age metadata.
5. Always output strictly valid JSON conforming exactly to the requested output structure.
"""

PROMPT_TEMPLATES: Dict[str, str] = {
    "product_analysis_v1": """Analyze the following verified Unified Product Intelligence record:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

INSTRUCTIONS:
- Evaluate product positioning, pricing parity across platforms, data completeness, and competitive viability.
- Formulate actionable, realistic strategic advice for e-commerce merchants and brand managers.
- Do NOT fabricate sales volumes or unverified market share numbers.

OUTPUT FORMAT (Respond with strictly valid JSON only):
{{
  "summary": "High-signal executive synthesis of product health and performance across platforms.",
  "category": "{category}",
  "confidence_score": 0.95,
  "key_signals": [
    "Signal 1 based on actual data",
    "Signal 2 based on actual data"
  ],
  "opportunities": [
    "Realistic opportunity 1",
    "Realistic opportunity 2"
  ],
  "risks": [
    "Identified risk 1 based on verified data",
    "Identified risk 2"
  ],
  "recommendations": [
    "Specific actionable recommendation 1",
    "Specific actionable recommendation 2"
  ],
  "pricing_analysis": {{
    "price_tier": "Mid-Market | Budget | Premium",
    "cross_platform_variance": "Description of price differences across platforms",
    "discount_effectiveness": "Analysis of active discounts"
  }}
}}""",

    "product_summary_v1": """Generate a concise executive summary for the following Unified Product:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

INSTRUCTIONS:
- Synthesize product attributes, audience target, competitive edge, and key takeaways.
- Base observations only on verified fields.

OUTPUT FORMAT (Strictly valid JSON):
{{
  "executive_summary": "Concise 2-3 sentence overview of this product's market presence.",
  "key_takeaways": [
    "Takeaway 1",
    "Takeaway 2",
    "Takeaway 3"
  ],
  "target_audience": "Primary demographic/customer profile for this item",
  "competitive_edge": "Primary value proposition or differentiating factor"
}}""",

    "category_analysis_v1": """Conduct a category-level market intelligence evaluation for the '{category}' sector based on the supplied multi-platform records:

[STRUCTURED CATEGORY CONTEXT]
{context_json}

INSTRUCTIONS:
- Analyze demand indicators, pricing spectrum, growth tailwinds, and risks.
- Do not fabricate industry-wide GMV or sales numbers.

OUTPUT FORMAT (Strictly valid JSON):
{{
  "category": "{category}",
  "market_overview": "Comprehensive assessment of category activity and maturity.",
  "demand_state": "High Steady Demand | Emerging Niche | Saturated | Seasonal",
  "price_range_summary": "Observed price range and median pricing in verified category data.",
  "growth_drivers": [
    "Driver 1",
    "Driver 2"
  ],
  "threats_and_challenges": [
    "Threat 1",
    "Threat 2"
  ],
  "strategic_advice": [
    "Strategic recommendation 1",
    "Strategic recommendation 2"
  ]
}}""",

    "market_comparison_v1": """Perform a detailed cross-platform market comparison across all active platform listings for this product:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

INSTRUCTIONS:
- Compare listing prices, currencies, seller types (marketplace reseller vs official DTC Shopify), stock availability, and rating distributions.
- Highlight arbitrage opportunities and distribution discrepancies.

OUTPUT FORMAT (Strictly valid JSON):
{{
  "cross_platform_overview": "Overview of how this product is distributed across platforms.",
  "price_arbitrage_analysis": "Detailed evaluation of price variances across platforms.",
  "seller_and_vendor_landscape": "Analysis of sellers, vendors, and fulfillment credibility.",
  "platform_comparison_breakdown": [
    {{
      "platform": "Platform Name",
      "competitive_strength": "Strength on this channel",
      "risk_factor": "Channel risk factor"
    }}
  ],
  "recommendations": [
    "Cross-channel optimization step 1",
    "Cross-channel optimization step 2"
  ]
}}""",

    "trend_analysis_v1": """Assess the price and demand trajectory for this unified product using verified historical snapshot observations:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

INSTRUCTIONS:
- Analyze historical price stability, discounting trends, review velocity, and stock continuity over time.
- Provide a reasoned 30-day predictive outlook.

OUTPUT FORMAT (Strictly valid JSON):
{{
  "trend_trajectory": "Rising Momentum | Stable Growth | Saturated / Stagnant | High Volatility",
  "velocity_assessment": "Assessment of customer review accumulation and price updates.",
  "volatility_risk": "Low | Moderate | High",
  "historical_price_action": "Summary of observed price fluctuations over recorded snapshots.",
  "predictive_outlook_30d": "Reasoned trajectory projection for the upcoming 30 days."
}}""",

    "report_generation_v1": """Generate a structured multi-page intelligence dossier for the following product entity:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

OUTPUT FORMAT (Strictly valid JSON):
{{
  "title": "Comprehensive Intelligence Report",
  "executive_brief": "Executive brief",
  "market_dynamics": "Market dynamics analysis",
  "action_plan": [
    "Immediate action",
    "30-day milestone",
    "90-day strategy"
  ]
}}""",

    "recommendation_v1": """Formulate tactical optimization recommendations for:

[STRUCTURED PRODUCT CONTEXT]
{context_json}

OUTPUT FORMAT (Strictly valid JSON):
{{
  "action_items": [
    {{
      "priority": "High | Medium | Low",
      "area": "Pricing | Content | Inventory | Channel Expansion",
      "action": "Description of action",
      "expected_impact": "Expected outcome"
    }}
  ]
}}"""
}


def get_prompt_template(name: str) -> str:
    """Retrieve a versioned prompt template by identifier."""
    if name not in PROMPT_TEMPLATES:
        raise KeyError(f"Prompt template '{name}' not found. Available: {list(PROMPT_TEMPLATES.keys())}")
    return PROMPT_TEMPLATES[name]
