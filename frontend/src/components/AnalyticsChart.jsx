import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function EmptyState({ message }) {
  return (
    <div className="flex h-[260px] items-center justify-center rounded-lg border border-dashed border-slate-700 px-4 text-center text-sm text-slate-400 sm:h-[280px]">
      {message}
    </div>
  );
}

function formatTooltipValue(value, unit) {
  if (typeof value !== "number") {
    return value;
  }
  return unit ? `${value}${unit}` : value;
}

export default function AnalyticsChart({
  title,
  type = "bar",
  data = [],
  xKey = "name",
  dataKey = "value",
  series = [],
  colors = ["#2dd4bf", "#60a5fa", "#f59e0b", "#f472b6", "#34d399", "#a78bfa"],
  unit = "",
  height = 300,
  emptyMessage = "No chart data available.",
  className = "",
}) {
  const chartSeries = series.length > 0 ? series : [{ key: dataKey, name: dataKey, color: colors[0] }];

  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900/70 p-4 ${className}`}>
      <header className="mb-4">
        <h3 className="text-base font-semibold text-white">{title}</h3>
      </header>

      {!Array.isArray(data) || data.length === 0 ? (
        <EmptyState message={emptyMessage} />
      ) : (
        <div className="w-full" style={{ height }}>
          <ResponsiveContainer>
            {type === "pie" ? (
              <PieChart>
                <Pie
                  data={data}
                  dataKey={dataKey}
                  nameKey={xKey}
                  innerRadius={55}
                  outerRadius={95}
                  paddingAngle={3}
                >
                  {data.map((entry, index) => (
                    <Cell
                      key={`${entry?.[xKey] || "segment"}-${index}`}
                      fill={colors[index % colors.length]}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatTooltipValue(value, unit)} />
                <Legend />
              </PieChart>
            ) : type === "line" ? (
              <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey={xKey} stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip formatter={(value) => formatTooltipValue(value, unit)} />
                <Legend />
                {chartSeries.map((item, index) => (
                  <Line
                    key={item.key}
                    type="monotone"
                    dataKey={item.key}
                    name={item.name}
                    stroke={item.color || colors[index % colors.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            ) : (
              <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey={xKey} stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip formatter={(value) => formatTooltipValue(value, unit)} />
                <Legend />
                {chartSeries.map((item, index) => (
                  <Bar
                    key={item.key}
                    dataKey={item.key}
                    name={item.name}
                    fill={item.color || colors[index % colors.length]}
                    radius={[6, 6, 0, 0]}
                  />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
