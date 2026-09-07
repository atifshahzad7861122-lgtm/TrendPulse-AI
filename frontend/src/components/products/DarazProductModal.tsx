import React, { useState, useEffect } from "react";
import { darazService } from "../../services/domainServices";
import type { DarazProductDetails } from "../../types";
import { LoadingSpinner } from "../common/StateComponents";

interface DarazProductModalProps {
  itemId: string;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Recursive Specification Formatter Component.
 * Safely renders nested objects, arrays, and primitive values without ever rendering "[object Object]".
 */
export const SpecValueRenderer: React.FC<{ label?: string; value: unknown; depth?: number }> = ({
  label,
  value,
  depth = 0,
}) => {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  // Handle Arrays
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    return (
      <div className={`space-y-1 ${depth > 0 ? "pl-3 border-l border-outline-variant/20 my-1" : ""}`}>
        {label && <span className="text-[11px] font-medium text-on-surface-variant">{label}:</span>}
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {value.map((item, idx) => (
            typeof item === "object" && item !== null ? (
              <div key={idx} className="w-full">
                <SpecValueRenderer value={item} depth={depth + 1} />
              </div>
            ) : (
              <span
                key={idx}
                className="inline-block px-2 py-0.5 rounded bg-surface-container text-on-surface text-[11px] font-mono-data border border-outline-variant/15"
              >
                {String(item)}
              </span>
            )
          ))}
        </div>
      </div>
    );
  }

  // Handle Nested Objects
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, v]) => v !== null && v !== undefined && v !== ""
    );
    if (entries.length === 0) return null;

    return (
      <div className={`space-y-1.5 ${depth > 0 ? "pl-3 border-l border-outline-variant/20 my-1.5" : ""}`}>
        {label && (
          <span className="text-xs font-semibold text-primary uppercase font-label-caps tracking-wider block">
            {label}
          </span>
        )}
        <div className="space-y-1">
          {entries.map(([subKey, subVal]) => (
            <div key={subKey} className="text-xs">
              <SpecValueRenderer label={subKey} value={subVal} depth={depth + 1} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Handle Primitives (String, Number, Boolean)
  return (
    <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between py-1 border-b border-outline-variant/10 text-xs">
      {label && <span className="text-on-surface-variant font-medium text-[11px] sm:pr-3">{label}</span>}
      <span className="text-on-surface font-semibold text-right break-words">{String(value)}</span>
    </div>
  );
};

export const DarazProductModal: React.FC<DarazProductModalProps> = ({ itemId, isOpen, onClose }) => {
  const [details, setDetails] = useState<DarazProductDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imageLoadError, setImageLoadError] = useState(false);

  useEffect(() => {
    if (!isOpen || !itemId) return;

    const fetchDetails = async () => {
      setLoading(true);
      setError(null);
      setImageLoadError(false);
      try {
        const cleanId = itemId.startsWith("daraz_") ? itemId.replace("daraz_", "") : itemId;
        const res = await darazService.getDetails(cleanId);
        if (res.success && res.data) {
          setDetails(res.data);
          const firstImage = res.data.main_image || res.data.images?.[0] || null;
          setSelectedImage(firstImage);
        } else {
          setError(res.message || "Unable to retrieve real-time details from Daraz Pakistan.");
        }
      } catch (err: any) {
        setError(err.message || "Error communicating with Daraz Pakistan connector");
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [itemId, isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface-container-high border border-outline-variant/30 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container">
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 rounded-full bg-[#f85606]/20 text-[#f85606] font-mono-data text-xs font-bold border border-[#f85606]/30 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#f85606] animate-pulse"></span>
              Daraz Pakistan Live Marketplace
            </span>
            <span className="text-xs text-on-surface-variant font-mono-data hidden sm:inline">
              Item ID: {itemId.replace("daraz_", "")}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-surface-container-highest text-on-surface-variant hover:text-on-surface transition-colors"
            title="Close modal"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="py-16">
              <LoadingSpinner size="lg" label="Fetching live specs from Daraz Pakistan..." />
            </div>
          ) : error ? (
            <div className="py-12 text-center space-y-3">
              <span className="material-symbols-outlined text-error text-5xl">error</span>
              <h3 className="text-lg font-bold text-on-surface">Data Unavailable</h3>
              <p className="text-xs text-on-surface-variant max-w-md mx-auto">{error}</p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 bg-surface-container-highest text-on-surface rounded-xl text-xs font-semibold hover:bg-surface-container transition-colors"
              >
                Close
              </button>
            </div>
          ) : details ? (
            <div className="space-y-6">
              {/* Product Overview Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Images Section */}
                <div className="space-y-3">
                  <div className="h-72 w-full bg-surface-container-lowest rounded-2xl overflow-hidden border border-outline-variant/20 flex items-center justify-center relative">
                    {selectedImage && !imageLoadError ? (
                      <img
                        src={selectedImage}
                        alt={details.name}
                        onError={() => setImageLoadError(true)}
                        className="w-full h-full object-contain p-2"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center p-6 text-center space-y-2">
                        <span className="material-symbols-outlined text-4xl text-on-surface-variant/40">
                          image_not_supported
                        </span>
                        <span className="text-xs text-on-surface-variant/70 font-mono-data">
                          Image unavailable
                        </span>
                      </div>
                    )}
                    {details.discount > 0 && (
                      <span className="absolute top-3 left-3 bg-[#f85606] text-white text-xs font-bold font-mono-data px-2.5 py-1 rounded-lg shadow-md">
                        {details.discount_label || `-${Math.round(details.discount)}%`}
                      </span>
                    )}
                  </div>

                  {details.images && details.images.length > 1 && (
                    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
                      {details.images.map((img, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => {
                            setSelectedImage(img);
                            setImageLoadError(false);
                          }}
                          className={`w-16 h-16 rounded-xl overflow-hidden border flex-shrink-0 transition-all ${
                            selectedImage === img
                              ? "border-[#f85606] ring-2 ring-[#f85606]/30"
                              : "border-outline-variant/20 hover:border-outline-variant opacity-70 hover:opacity-100"
                          }`}
                        >
                          <img src={img} alt="" className="w-full h-full object-cover" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Info Section */}
                <div className="space-y-4 flex flex-col justify-between">
                  <div className="space-y-2">
                    {details.brand && (
                      <span className="text-[11px] font-mono-data uppercase text-primary tracking-wider font-semibold">
                        {details.brand}
                      </span>
                    )}
                    <h2 className="text-lg md:text-xl font-bold text-on-surface leading-snug">
                      {details.name}
                    </h2>

                    {/* Rating & Stock */}
                    <div className="flex items-center gap-3 pt-1 flex-wrap">
                      <div className="flex items-center gap-1 bg-amber-500/10 text-amber-500 px-2 py-0.5 rounded-lg border border-amber-500/20 text-xs font-mono-data font-bold">
                        <span className="material-symbols-outlined text-xs">star</span>
                        {details.rating > 0 ? details.rating.toFixed(1) : "New"}
                      </div>
                      {details.review_count > 0 && (
                        <span className="text-xs text-on-surface-variant font-mono-data">
                          ({details.review_count} reviews)
                        </span>
                      )}
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-mono-data font-semibold ${
                          details.in_stock
                            ? "bg-success/10 text-success border border-success/20"
                            : "bg-error/10 text-error border border-error/20"
                        }`}
                      >
                        {details.in_stock ? "In Stock" : "Out of Stock"}
                      </span>
                    </div>
                  </div>

                  {/* Price Banner */}
                  <div className="p-4 rounded-2xl bg-surface-container border border-outline-variant/20 flex items-baseline justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-label-caps text-on-surface-variant">
                        Current Price
                      </span>
                      <div className="flex items-baseline gap-2 mt-0.5">
                        {details.price > 0 ? (
                          <span className="text-2xl font-bold font-mono-data text-[#f85606]">
                            PKR {details.price.toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-lg font-bold font-mono-data text-on-surface-variant">
                            Price unavailable
                          </span>
                        )}
                        {details.original_price > details.price && details.original_price > 0 && (
                          <span className="text-xs font-mono-data line-through text-on-surface-variant">
                            PKR {details.original_price.toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                    {details.warranty && (
                      <div className="text-right max-w-[45%]">
                        <span className="text-[10px] uppercase font-label-caps text-on-surface-variant">
                          Warranty & Return
                        </span>
                        <p className="text-xs font-semibold text-on-surface truncate">{details.warranty}</p>
                      </div>
                    )}
                  </div>

                  {/* Seller Metrics */}
                  {details.seller && (
                    <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/20 space-y-2">
                      <div className="flex items-center justify-between">
                        {details.seller.seller_url ? (
                          <a
                            href={details.seller.seller_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs font-bold text-on-surface hover:text-[#f85606] transition-colors flex items-center gap-1.5"
                          >
                            <span className="material-symbols-outlined text-sm text-primary">store</span>
                            {details.seller.name || "Daraz Verified Merchant"}
                            <span className="material-symbols-outlined text-[10px]">open_in_new</span>
                          </a>
                        ) : (
                          <span className="text-xs font-bold text-on-surface flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm text-primary">store</span>
                            {details.seller.name || "Daraz Verified Merchant"}
                          </span>
                        )}
                        {details.seller.positive_seller_rating && (
                          <span className="text-xs font-mono-data text-success font-semibold">
                            {details.seller.positive_seller_rating} Positive
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-outline-variant/15 text-[11px] text-on-surface-variant">
                        {details.seller.ship_on_time && (
                          <div>
                            <span>Ship on Time: </span>
                            <strong className="text-on-surface">{details.seller.ship_on_time}</strong>
                          </div>
                        )}
                        {details.seller.chat_response_rate && (
                          <div>
                            <span>Chat Response: </span>
                            <strong className="text-on-surface">{details.seller.chat_response_rate}</strong>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Buy on Daraz CTA */}
                  {details.product_url && (
                    <a
                      href={details.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full bg-[#f85606] hover:bg-[#e04e05] text-white font-label-caps text-xs py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 shadow-lg transition-all hover:shadow-orange-500/25"
                    >
                      <span>View & Buy on Daraz.pk</span>
                      <span className="material-symbols-outlined text-sm">open_in_new</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Highlights Bullet Points */}
              {details.highlights && details.highlights.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-outline-variant/20">
                  <h4 className="text-xs font-bold text-on-surface uppercase font-label-caps">
                    Key Highlights
                  </h4>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {details.highlights.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-on-surface-variant">
                        <span className="text-[#f85606] font-bold mt-0.5">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* SKU Variants if any */}
              {details.sku_variants && details.sku_variants.length > 1 && (
                <div className="space-y-2 pt-2 border-t border-outline-variant/20">
                  <h4 className="text-xs font-bold text-on-surface uppercase font-label-caps">
                    Available SKU Variants ({details.sku_variants.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {details.sku_variants.map((v, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-2 rounded-xl bg-surface-container border border-outline-variant/20 text-xs font-mono-data flex items-center gap-2"
                      >
                        <span className="text-on-surface font-medium">{v.sku_name || `Variant ${idx + 1}`}</span>
                        {v.price && (
                          <span className="text-[#f85606] font-bold">
                            PKR {v.price.toLocaleString()}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recursive Specifications Viewer */}
              {details.specifications && Object.keys(details.specifications).length > 0 && (
                <div className="space-y-3 pt-2 border-t border-outline-variant/20">
                  <h4 className="text-xs font-bold text-on-surface uppercase font-label-caps">
                    Specifications & Product Details
                  </h4>
                  <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/20 text-xs space-y-1">
                    {Object.entries(details.specifications).map(([key, val]) => (
                      <SpecValueRenderer key={key} label={key} value={val} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
