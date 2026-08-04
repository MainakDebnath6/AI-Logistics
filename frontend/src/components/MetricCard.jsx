const colorMap = {
  teal: {
    ring: "ring-teal-500/25",
    icon: "bg-teal-500/15 text-teal-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
  blue: {
    ring: "ring-sky-500/25",
    icon: "bg-sky-500/15 text-sky-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
  violet: {
    ring: "ring-violet-500/25",
    icon: "bg-violet-500/15 text-violet-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
  emerald: {
    ring: "ring-emerald-500/25",
    icon: "bg-emerald-500/15 text-emerald-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
  amber: {
    ring: "ring-amber-500/25",
    icon: "bg-amber-500/15 text-amber-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
  cyan: {
    ring: "ring-cyan-500/25",
    icon: "bg-cyan-500/15 text-cyan-300",
    trendUp: "text-emerald-300",
    trendDown: "text-rose-300",
    trendFlat: "text-slate-300",
  },
};

function getTrendDirection(trend) {
  if (typeof trend === "object" && trend?.direction) {
    return trend.direction;
  }
  if (typeof trend === "number") {
    if (trend > 0) {
      return "up";
    }
    if (trend < 0) {
      return "down";
    }
  }
  return "flat";
}

function getTrendLabel(trend) {
  if (trend === null || trend === undefined) {
    return "";
  }
  if (typeof trend === "object") {
    return trend.label || "";
  }
  if (typeof trend === "number") {
    const sign = trend > 0 ? "+" : "";
    return `${sign}${trend.toFixed(1)}%`;
  }
  return String(trend);
}

export default function MetricCard({
  title,
  value,
  icon,
  color = "teal",
  trend,
  subtitle,
  className = "",
}) {
  const palette = colorMap[color] || colorMap.teal;
  const direction = getTrendDirection(trend);
  const trendLabel = getTrendLabel(trend);

  return (
    <article
      className={`rounded-xl border border-slate-800 bg-slate-900/70 p-4 shadow-sm ring-1 ${palette.ring} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
          <p className="mt-2 text-2xl font-bold text-white sm:text-3xl">{value}</p>
        </div>

        {icon ? (
          <span
            className={`inline-flex h-10 w-10 items-center justify-center rounded-lg ${palette.icon}`}
            aria-hidden="true"
          >
            {icon}
          </span>
        ) : null}
      </div>

      {trendLabel ? (
        <p
          className={`mt-3 text-sm ${
            direction === "up"
              ? palette.trendUp
              : direction === "down"
                ? palette.trendDown
                : palette.trendFlat
          }`}
        >
          {direction === "up" ? "↑ " : direction === "down" ? "↓ " : "→ "}
          {trendLabel}
        </p>
      ) : subtitle ? (
        <p className="mt-3 text-sm text-slate-300">{subtitle}</p>
      ) : null}
    </article>
  );
}
