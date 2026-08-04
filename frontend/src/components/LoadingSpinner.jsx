export default function LoadingSpinner({
  size = "md",
  label = "Loading...",
  fullScreen = false,
}) {
  const sizeClass = {
    sm: "h-4 w-4 border-2",
    md: "h-6 w-6 border-2",
    lg: "h-10 w-10 border-4",
  }[size] || "h-6 w-6 border-2";

  const containerClass = fullScreen
    ? "flex min-h-[40vh] items-center justify-center"
    : "flex items-center justify-center";

  return (
    <div className={containerClass} role="status" aria-live="polite">
      <div className="flex items-center gap-3 text-slate-300">
        <span
          className={`${sizeClass} inline-block animate-spin rounded-full border-slate-700 border-t-teal-400`}
          aria-hidden="true"
        />
        <span className="text-sm font-medium">{label}</span>
      </div>
    </div>
  );
}
