import React from "react";
import { Link } from "react-router-dom";

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-background font-body-md text-on-surface antialiased overflow-x-hidden">
      {/* Top Header */}
      <header className="fixed top-0 w-full z-50 bg-background/80 backdrop-blur-xl border-b border-outline-variant/15 transition-all">
        <div className="h-20 max-w-[1440px] mx-auto px-6 md:px-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary-container/20 border border-primary/40 flex items-center justify-center text-primary shadow-[0_0_15px_rgba(223,115,40,0.2)]">
              <span className="material-symbols-outlined text-xl">radar</span>
            </div>
            <span className="font-headline-sm text-lg font-bold text-on-surface">
              TrendPulse <span className="text-primary">AI</span>
            </span>
          </div>

          <nav className="hidden lg:flex items-center gap-8 text-xs font-label-caps">
            <a href="#product" className="text-on-surface-variant hover:text-primary transition-colors">
              Product
            </a>
            <a href="#intelligence" className="text-on-surface-variant hover:text-primary transition-colors">
              Intelligence
            </a>
            <a href="#how-it-works" className="text-on-surface-variant hover:text-primary transition-colors">
              How It Works
            </a>
            <a href="#data-sources" className="text-on-surface-variant hover:text-primary transition-colors">
              Data Sources
            </a>
            <a href="#reports" className="text-on-surface-variant hover:text-primary transition-colors">
              Reports
            </a>
            <Link to="/transparency" className="text-rose-400/90 hover:text-rose-300 transition-colors flex items-center gap-1 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
              DQ Audit
            </Link>
          </nav>


          <div className="flex items-center gap-6">
            <Link
              to="/login"
              className="text-xs font-label-caps text-on-surface-variant hover:text-primary transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/register"
              className="bg-primary text-on-primary font-label-caps text-xs px-5 py-2.5 rounded-full hover:bg-primary-container hover:text-on-primary-container transition-all shadow-[0_0_20px_rgba(255,182,141,0.25)] font-semibold"
            >
              Start Free
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="pt-20">
        {/* Live Ticker */}
        <div className="w-full bg-surface-container-low border-b border-primary/10 py-3 overflow-hidden relative z-20">
          <div className="flex whitespace-nowrap animate-ticker gap-12 font-mono-data text-xs text-primary">
            <span className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(255,182,141,0.8)]" />
              SIGNAL: Activewear Lip Serums +340% (TikTok)
            </span>
            <span>•</span>
            <span className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(255,182,141,0.8)]" />
              TREND: Matcha preparation sets surging on Instagram
            </span>
            <span>•</span>
            <span className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(255,182,141,0.8)]" />
              ALERT: Micro-mobility search volume peak (+218% YoY)
            </span>
            <span>•</span>
            <span className="flex items-center gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(255,182,141,0.8)]" />
              VELOCITY: Modular MagSafe Stands up 185% WoW
            </span>
          </div>
        </div>

        {/* Hero Section */}
        <section className="relative pt-24 pb-32 px-6 md:px-16 max-w-[1440px] mx-auto w-full flex flex-col items-center text-center">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background pointer-events-none" />
          <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[140px] pointer-events-none animate-pulse-glow" />

          <div className="max-w-4xl z-10 space-y-8 flex flex-col items-center">
            <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full border border-primary/25 bg-surface-container-low text-label-caps text-xs text-primary shadow-[0_0_20px_rgba(255,182,141,0.15)] font-semibold">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              ALL INTELLIGENCE FEEDS OPERATIONAL
            </div>

            <h1 className="font-display-lg text-5xl md:text-7xl lg:text-8xl tracking-tight text-on-surface text-balance font-extrabold leading-none">
              Understand the market{" "}
              <span className="block text-primary italic font-editorial-italic font-normal mt-2 drop-shadow-[0_0_30px_rgba(255,182,141,0.25)]">
                before it moves.
              </span>
            </h1>

            <p className="font-body-lg text-on-surface-variant max-w-2xl text-lg md:text-xl leading-relaxed">
              TrendPulse AI transforms social signals, platform activity, cross-border retail velocity, and consumer sentiment into actionable market intelligence.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <Link
                to="/register"
                className="bg-primary text-on-primary font-label-caps px-8 py-4 rounded-full hover:bg-primary-container hover:text-on-primary-container transition-all shadow-[0_0_30px_rgba(255,182,141,0.3)] flex items-center gap-2 font-semibold text-xs"
              >
                Start Free Analysis
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </Link>
              <a
                href="#intelligence"
                className="bg-surface-container border border-primary/20 text-on-surface font-label-caps px-8 py-4 rounded-full hover:bg-surface-container-high hover:border-primary/40 transition-all text-xs font-semibold"
              >
                Explore Intelligence
              </a>
            </div>
          </div>

          {/* Interactive Live Preview Card */}
          <div id="product" className="w-full max-w-5xl mt-24 relative z-10 text-left">
            <div className="bg-surface-container-low rounded-3xl p-1 border border-primary/20 shadow-2xl glass-panel">
              <div className="bg-surface rounded-2xl overflow-hidden p-6 md:p-8">
                <div className="flex items-center justify-between border-b border-outline-variant/20 pb-4 mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
                    <span className="text-xs font-label-caps text-on-surface-variant tracking-widest uppercase">
                      LIVE PREVIEW FEED
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-surface-variant" />
                    <div className="w-3 h-3 rounded-full bg-surface-variant" />
                    <div className="w-3 h-3 rounded-full bg-surface-variant" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-surface-container-low p-5 rounded-xl border border-outline-variant/15">
                    <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
                      Top Breakout Signal
                    </span>
                    <h3 className="text-base font-bold text-on-surface mt-1">Wireless ANC Earbuds</h3>
                    <div className="text-2xl font-mono-data font-bold text-primary mt-3 flex items-baseline gap-2">
                      96.4
                      <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                        +340% YoY
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-2">
                      Cross-platform engagement spike on TikTok & Daraz.
                    </p>
                  </div>

                  <div className="bg-surface-container-low p-5 rounded-xl border border-outline-variant/15">
                    <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
                      Active Signal Points
                    </span>
                    <h3 className="text-base font-bold text-on-surface mt-1">Multi-Channel Ingestion</h3>
                    <div className="text-2xl font-mono-data font-bold text-primary mt-3 flex items-baseline gap-2">
                      1.84M
                      <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                        Real-time
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-2">
                      Ingesting from TikTok, Daraz, Instagram & YouTube.
                    </p>
                  </div>

                  <div className="bg-surface-container-low p-5 rounded-xl border border-outline-variant/15">
                    <span className="text-[11px] font-label-caps text-on-surface-variant uppercase">
                      First-Mover Window
                    </span>
                    <h3 className="text-base font-bold text-on-surface mt-1">Arbitrage Opportunity</h3>
                    <div className="text-2xl font-mono-data font-bold text-primary mt-3 flex items-baseline gap-2">
                      3-5 Wks
                      <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                        High Conviction
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant mt-2">
                      Low domestic competition saturation detected.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works / Intelligence Architecture Section */}
        <section id="intelligence" className="py-24 px-6 md:px-16 max-w-[1440px] mx-auto border-t border-outline-variant/15">
          <div id="how-it-works" className="scroll-mt-24 text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
              FOUR-STAGE INTELLIGENCE PIPELINE
            </span>
            <h2 className="text-3xl md:text-5xl font-headline-md font-bold mt-3 text-on-surface">
              From raw social buzz to high-conviction product arbitrage
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              {
                step: "01",
                title: "Multi-Source Signal Ingestion",
                desc: "Real-time scrapers stream engagement metrics from TikTok, Daraz, Instagram, YouTube, and Facebook.",
                icon: "hub",
              },
              {
                step: "02",
                title: "Velocity & Anomaly Detection",
                desc: "Algorithms filter organic spikes from artificial bot noise and calculate compound growth rates.",
                icon: "speed",
              },
              {
                step: "03",
                title: "AI Synthesis & Market Context",
                desc: "LLM contextualization generates human-readable strategic breakdowns and saturation timelines.",
                icon: "psychology",
              },
              {
                step: "04",
                title: "Automated Executive Briefings",
                desc: "Instant exportable PDF & CSV reports equipped with sourcing advice and margin forecasts.",
                icon: "description",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/20 glass-card"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono-data text-primary font-bold">{item.step}</span>
                  <span className="material-symbols-outlined text-primary text-2xl">{item.icon}</span>
                </div>
                <h3 className="text-base font-bold text-on-surface mb-2">{item.title}</h3>
                <p className="text-xs text-on-surface-variant leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Data Sources Grid Section */}
        <section id="data-sources" className="py-24 px-6 md:px-16 max-w-[1440px] mx-auto border-t border-outline-variant/15">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
              CONNECTED ECOSYSTEM
            </span>
            <h2 className="text-3xl md:text-5xl font-headline-md font-bold mt-3 text-on-surface">
              Monitoring the platforms that define consumer demand
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { name: "TikTok", count: "842K Signals", growth: "+48.2%", icon: "tiktok" },
              { name: "Daraz Marketplace", count: "512K Signals", growth: "+32.4%", icon: "shopping_bag" },
              { name: "Instagram Reels", count: "420K Signals", growth: "+26.8%", icon: "photo_camera" },
              { name: "YouTube", count: "290K Signals", growth: "+19.5%", icon: "smart_display" },
            ].map((src) => (
              <div
                key={src.name}
                className="bg-surface-container p-6 rounded-2xl border border-outline-variant/20 text-center glass-card"
              >
                <div className="w-12 h-12 mx-auto rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-3">
                  <span className="material-symbols-outlined text-2xl">{src.icon}</span>
                </div>
                <h4 className="text-sm font-bold text-on-surface">{src.name}</h4>
                <p className="text-xs font-mono-data text-primary mt-1">{src.growth} WoW</p>
                <p className="text-[11px] text-on-surface-variant mt-1">{src.count}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Reports Showcase Section */}
        <section id="reports" className="py-24 px-6 md:px-16 max-w-[1440px] mx-auto border-t border-outline-variant/15">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
              INTELLIGENCE DOSSIERS
            </span>
            <h2 className="text-3xl md:text-5xl font-headline-md font-bold mt-3 text-on-surface">
              Actionable dossiers tailored for cross-border decision makers
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: "Executive Opportunity Brief",
                desc: "High-level overview of velocity surges, gross margin opportunities, and initial supplier lead times.",
                badge: "Executive",
              },
              {
                title: "Platform Arbitrage Breakdown",
                desc: "Granular viral velocity comparison across TikTok virality vs Daraz marketplace product listings.",
                badge: "Deep Dive",
              },
              {
                title: "Category Saturation Matrix",
                desc: "Calculated first-mover opportunity windows and predicted price saturation inflection points.",
                badge: "Strategy",
              },
            ].map((rep, idx) => (
              <div key={idx} className="bg-surface-container p-6 rounded-2xl border border-outline-variant/20 glass-card flex flex-col justify-between">
                <div>
                  <span className="text-[10px] font-label-caps text-primary bg-primary/10 px-2.5 py-1 rounded-full border border-primary/20">
                    {rep.badge}
                  </span>
                  <h3 className="text-base font-bold text-on-surface mt-3">{rep.title}</h3>
                  <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">{rep.desc}</p>
                </div>
                <div className="pt-6 border-t border-outline-variant/10 mt-6 flex items-center justify-between text-xs text-primary font-semibold">
                  <span>Export Formats: PDF, CSV, JSON</span>
                  <span className="material-symbols-outlined text-sm">download</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ Section with Interactive Accordions */}
        <section id="faq" className="py-24 px-6 md:px-16 max-w-[1000px] mx-auto border-t border-outline-variant/15">
          <div className="text-center mb-12">
            <span className="text-xs font-label-caps text-primary uppercase tracking-widest">
              FREQUENTLY ASKED QUESTIONS
            </span>
            <h2 className="text-3xl md:text-4xl font-headline-md font-bold mt-3 text-on-surface">
              Everything you need to know about TrendPulse AI
            </h2>
          </div>

          <div className="space-y-4">
            <FaqAccordion
              question="How does TrendPulse AI detect breakout products early?"
              answer="Our multi-channel scrapers continuously ingest social video engagement, hashtag acceleration, and e-commerce velocity. When an anomaly is detected before retail saturation, our LLM engine synthesizes an intelligence dossier."
            />
            <FaqAccordion
              question="Which e-commerce platforms and social channels are tracked?"
              answer="Currently TrendPulse AI ingests data from TikTok, Daraz, Instagram Reels, YouTube, and Facebook, providing cross-channel sentiment and product demand correlation."
            />
            <FaqAccordion
              question="Can I export dossiers and custom reports?"
              answer="Yes. Every intelligence dossier and dashboard slice can be instantly exported as structured JSON, CSV datasets, or high-fidelity executive PDF briefings."
            />
            <FaqAccordion
              question="How does the workspace and team management operate?"
              answer="Each organization configures a dedicated workspace with tailored industry taxonomies, local currencies, preferred default dashboards, and custom alert thresholds."
            />
          </div>
        </section>

        {/* Bottom CTA Banner */}
        <section className="py-24 px-6 md:px-16 max-w-[1440px] mx-auto">
          <div className="bg-surface-container rounded-3xl p-12 md:p-16 border border-primary/30 text-center relative overflow-hidden glass-panel">
            <div className="absolute top-0 right-0 w-96 h-96 bg-primary/15 rounded-full blur-3xl pointer-events-none" />
            <h2 className="text-3xl md:text-5xl font-headline-md font-bold text-on-surface max-w-2xl mx-auto">
              Ready to predict your next breakout category?
            </h2>
            <p className="text-sm md:text-base text-on-surface-variant max-w-xl mx-auto mt-4">
              Join leading e-commerce operators, brand managers, and sourcing strategists powered by TrendPulse AI.
            </p>
            <div className="flex justify-center gap-4 mt-8">
              <Link
                to="/register"
                className="bg-primary text-on-primary font-label-caps text-xs font-semibold px-8 py-4 rounded-full hover:bg-primary-container transition-all shadow-[0_0_25px_rgba(255,182,141,0.3)]"
              >
                Create Free Workspace
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-outline-variant/15 py-12 px-6 md:px-16 bg-surface-container-lowest">
        <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-on-surface-variant">
          <div className="flex items-center gap-2">
            <span className="font-headline-sm font-bold text-on-surface">TrendPulse AI</span>
            <span>•</span>
            <span>Precision Market Intelligence Platform</span>
          </div>
          <div className="flex gap-6 font-label-caps text-[11px]">
            <Link to="/login" className="hover:text-primary transition-colors">Sign In</Link>
            <Link to="/register" className="hover:text-primary transition-colors">Register</Link>
            <a href="#product" className="hover:text-primary transition-colors">Product</a>
            <a href="#intelligence" className="hover:text-primary transition-colors">Intelligence</a>
            <a href="#faq" className="hover:text-primary transition-colors">FAQ</a>
          </div>
          <p className="font-mono-data text-[11px]">© 2026 TrendPulse AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

const FaqAccordion: React.FC<{ question: string; answer: string }> = ({ question, answer }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  return (
    <div className="border border-outline-variant/20 rounded-2xl bg-surface-container-low overflow-hidden transition-all">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-5 text-left flex items-center justify-between gap-4 font-semibold text-sm text-on-surface hover:text-primary transition-colors"
      >
        <span>{question}</span>
        <span className="material-symbols-outlined text-primary text-xl transition-transform duration-200" style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}>
          expand_more
        </span>
      </button>
      {isOpen && (
        <div className="px-5 pb-5 text-xs text-on-surface-variant leading-relaxed border-t border-outline-variant/10 pt-3">
          {answer}
        </div>
      )}
    </div>
  );
};
