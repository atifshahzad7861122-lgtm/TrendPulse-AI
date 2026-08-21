import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { searchService } from "../../services/domainServices";
import type { SearchResultItem } from "../../types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandSearchModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleEsc);
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setResults([]);
    }
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchService.search(query);
        if (res.success && res.data) {
          setResults(res.data.results);
        }
      } catch (err) {
        console.error("Search failed", err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  if (!isOpen) return null;

  const handleSelect = (link: string) => {
    onClose();
    navigate(link);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-surface-container border border-primary/20 rounded-2xl shadow-2xl overflow-hidden glass-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center px-4 py-3.5 border-b border-outline-variant/20 gap-3">
          <span className="material-symbols-outlined text-primary text-xl">search</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search products, categories, platforms, reports, alerts..."
            value={query}
            maxLength={200}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent text-on-surface placeholder-on-surface-variant/60 focus:outline-none font-body-md text-sm"
          />
          {loading && <div className="w-4 h-4 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />}
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono-data bg-surface-container-high rounded border border-outline-variant/30 text-on-surface-variant">
            ESC
          </kbd>
          <button onClick={onClose} className="text-on-surface-variant hover:text-on-surface">
            <span className="material-symbols-outlined text-base">close</span>
          </button>
        </div>

        {/* Results Area */}
        <div className="max-h-96 overflow-y-auto p-2">
          {query.trim() === "" ? (
            <div className="p-8 text-center text-on-surface-variant text-xs">
              Type to search across intelligence datasets, platforms, and reports.
            </div>
          ) : loading ? (
            <div className="p-8 text-center text-on-surface-variant text-xs flex items-center justify-center gap-2">
              <div className="w-3.5 h-3.5 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
              Searching market signals...
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center text-on-surface-variant text-xs">
              No matching records found for "{query}".
            </div>
          ) : (
            <div className="space-y-1">
              {results.map((item) => (
                <button
                  key={`${item.category}-${item.id}`}
                  onClick={() => handleSelect(item.link)}
                  className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-surface-container-high/80 transition-colors text-left group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary group-hover:bg-primary/20 transition-colors">
                      <span className="material-symbols-outlined text-lg">
                        {item.category === "products"
                          ? "inventory_2"
                          : item.category === "categories"
                          ? "category"
                          : item.category === "platforms"
                          ? "share"
                          : item.category === "reports"
                          ? "description"
                          : "warning"}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-on-surface group-hover:text-primary transition-colors">
                        {item.title}
                      </p>
                      <p className="text-xs text-on-surface-variant">{item.subtitle}</p>
                    </div>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-label-caps uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 border-t border-outline-variant/20 bg-surface-container-lowest flex items-center justify-between text-[11px] font-mono-data text-on-surface-variant">
          <span>Global Search Command</span>
          <span>Press Enter to select</span>
        </div>
      </div>
    </div>
  );
};
