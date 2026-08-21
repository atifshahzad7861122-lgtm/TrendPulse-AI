# Specification: Phase 2A — Real Backend Business Logic & Intelligence Engines

## 1. Overview & Goal
Phase 2A elevates TrendPulse AI from functional UI contracts with static mock data to an active analytical platform powered by real backend intelligence calculations, mathematical scoring engines, cross-domain aggregations, dynamic report generation, normalized signal ingestion pipelines, and state synchronization.

## 2. In-Scope Functional Engines & Services
1. **Normalized Signal Model & Ingestion Pipeline**:
   - `PlatformSignal` internal schema (platform, product_id, category, timestamp, volume, engagement, velocity, raw_metric).
   - `DataSourceConnector` interface with concrete mock connectors (`MockTikTokConnector`, `MockDarazConnector`, `MockInstagramConnector`, `MockYouTubeConnector`, `MockFacebookConnector`).
   - Ingestion pipeline: `Connector -> Raw Data -> Normalizer -> Validator -> Repository -> Recalculation -> Alerts -> Dashboard`.
2. **Product Intelligence & Trend Scoring Engine**:
   - Deterministic mathematical models for:
     - **Velocity**: Rate of change of volume and mentions over time windows ($V = \frac{\Delta \text{Volume}}{\Delta t} \times \text{weight}$).
     - **Growth Rate**: Percentage change relative to baseline ($G = \frac{V_t - V_0}{V_0} \times 100\%$).
     - **Momentum**: Acceleration of velocity ($\Delta V / \Delta t$).
     - **Trend Score**: Composite multi-factor index ($S = w_v \cdot \text{NormalizedVelocity} + w_g \cdot \text{Growth} + w_s \cdot \text{Sentiment} + w_p \cdot \text{PlatformDispersion}$).
   - Multi-timeframe support: `7d`, `30d`, `all`.
3. **Demand Signal & Viral Potential Engines**:
   - **Demand Strength**: Categorized (`Low`, `Moderate`, `Strong`, `Very Strong`) with numerical confidence derived from sentiment, conversion volume, and search intent.
   - **Viral Potential**: Categorized (`Low`, `Moderate`, `High`, `Very High`) derived from velocity acceleration, cross-platform spread, and TikTok/Instagram engagement spikes.
4. **Platform & Category Intelligence**:
   - Dynamic aggregation of category metrics from underlying products (total products, average trend score, average demand, momentum, category growth).
   - Dynamic calculation of platform telemetry (total signals, active trends count, velocity growth, market share, recent spikes).
5. **Dashboard Analytics Engine**:
   - Dynamic real-time calculation of KPI metrics, area chart time-series curves, top surging products, and live signal stream driven by `7d`, `30d`, `all`, category, and platform filters.
6. **Product Discovery, Search & Comparison**:
   - Multi-attribute ranking search with query matching across title, category, tags, and AI summary.
   - 2-4 product head-to-head comparison engine computing aligned trajectory curves and dimensional matrices.
7. **Watchlist & Alert Engines**:
   - Watchlist state management preventing duplicate entries and syncing product watch status.
   - Alert evaluation engine detecting anomaly spikes (>200% growth, rapid sentiment shifts, inventory depletion).
8. **Intelligence Report Engine & Multi-Format Export**:
   - Multi-stage report generation processing real product/category/platform signals into structured executive dossiers.
   - Clean export in structured `JSON` and `CSV` formats.
9. **Pluggable AI Synthesis Interface**:
   - `AIInsightService` providing deterministic structured intelligence summaries based on calculated signal vectors.

## 3. Strict Boundary Constraints
- **PostgreSQL**: STRICTLY DEFERRED. In-memory thread-safe repositories are maintained behind clean repository interfaces.
- **External Network APIs**: STRICTLY DEFERRED. Realistic mock connectors simulate ingestion without live external network calls.
- **UI Visual Design**: Obsidian Copper Stitch UI is fully preserved without redesigns.
