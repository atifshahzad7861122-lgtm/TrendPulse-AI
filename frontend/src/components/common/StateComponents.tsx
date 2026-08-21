import React from "react";

export const LoadingSpinner: React.FC<{ size?: "sm" | "md" | "lg"; label?: string }> = ({
  size = "md",
  label,
}) => {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-8 h-8 border-2",
    lg: "w-12 h-12 border-3",
  }[size];

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-3">
      <div
        className={`${sizeClasses} rounded-full border-primary/20 border-t-primary animate-spin`}
      />
      {label && <p className="text-xs font-label-caps text-on-surface-variant tracking-wider">{label}</p>}
    </div>
  );
};

export const SkeletonLoader: React.FC<{ lines?: number; height?: string }> = ({
  lines = 3,
  height = "h-4",
}) => {
  return (
    <div className="space-y-3 w-full animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`${height} bg-surface-container-high/60 rounded ${
            i === lines - 1 ? "w-3/4" : "w-full"
          }`}
        />
      ))}
    </div>
  );
};

export const EmptyState: React.FC<{
  title: string;
  description: string;
  icon?: string;
  actionText?: string;
  onAction?: () => void;
}> = ({ title, description, icon = "inbox", actionText, onAction }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-outline-variant/30 rounded-xl bg-surface-container-low/40">
      <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center text-primary mb-4">
        <span className="material-symbols-outlined text-2xl">{icon}</span>
      </div>
      <h4 className="text-lg font-headline-sm font-semibold text-on-surface mb-2">{title}</h4>
      <p className="text-sm text-on-surface-variant max-w-md mb-6">{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="bg-primary text-on-primary font-label-caps text-xs px-5 py-2.5 rounded-lg hover:bg-primary-container transition-all"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  message?: string;
  onRetry?: () => void;
}> = ({ message = "Failed to load data from intelligence server", onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-10 text-center border border-error/30 rounded-xl bg-error-container/10">
      <div className="w-12 h-12 rounded-full bg-error-container flex items-center justify-center text-error mb-4">
        <span className="material-symbols-outlined text-2xl">error</span>
      </div>
      <h4 className="text-base font-semibold text-on-surface mb-1">Service Error Encountered</h4>
      <p className="text-xs text-on-surface-variant max-w-sm mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="bg-surface-container-high border border-primary/30 text-on-surface font-label-caps text-xs px-4 py-2 rounded-lg hover:border-primary transition-all flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">refresh</span>
          Retry Request
        </button>
      )}
    </div>
  );
};
