"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartView } from "./types";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DynamicChartProps {
  view: ChartView;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Strip common formatting characters from a string value to get a number. */
function parseNumeric(value: unknown): number {
  if (value === null || value === undefined) return 0;
  if (typeof value === "number") return value;
  if (typeof value !== "string") return 0;
  const cleaned = value.replace(/[$%,£€\s]/g, "").replace(/[()]/g, "");
  const num = Number(cleaned);
  return Number.isNaN(num) ? 0 : num;
}

/** Build chart-ready data from {headers, rows}. */
function buildChartData(headers: string[], rows: Record<string, string>[]) {
  const valueColumns = headers.filter((h) => h !== "id");
  const labelCol = valueColumns[0]; // first non-id column is the label
  const seriesCols = valueColumns.slice(1); // remaining columns are series

  return {
    data: rows.map((row) => {
      const point: Record<string, string | number> = {
        name: row[labelCol] ?? row.id,
      };
      for (const col of valueColumns) {
        point[col] = parseNumeric(row[col] ?? "");
      }
      return point;
    }),
    seriesCols: seriesCols.length > 0 ? seriesCols : [labelCol],
    labelCol,
  };
}

/** Color palette for charts. */
const COLORS = [
  "#B8860B", // brand
  "#3B6CB5", // info
  "#2D8A4E", // success
  "#C53030", // danger
  "#B85C0A", // warning
  "#5F6675", // text-secondary
  "#9DA3AE", // text-disabled
  "#1A1D26", // text-primary
];

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DynamicChart({ view }: DynamicChartProps) {
  const { chartType, headers, rows } = view.data;

  if (!rows || rows.length === 0) {
    return (
      <p className="text-sm text-[--text-disabled] text-center py-8">
        No data to chart
      </p>
    );
  }

  const { data, seriesCols } = buildChartData(headers, rows);

  /* ---- Bar chart ---- */
  if (chartType === "bar") {
    return (
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #E1E4E8)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "var(--text-secondary, #5F6675)" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "var(--text-secondary, #5F6675)" }}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-4, #FFFFFF)",
              border: "1px solid var(--border, #E1E4E8)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Legend />
          {seriesCols.map((col, i) => (
            <Bar
              key={col}
              dataKey={col}
              fill={COLORS[i % COLORS.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  /* ---- Line chart ---- */
  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #E1E4E8)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: "var(--text-secondary, #5F6675)" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "var(--text-secondary, #5F6675)" }}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-4, #FFFFFF)",
              border: "1px solid var(--border, #E1E4E8)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Legend />
          {seriesCols.map((col, i) => (
            <Line
              key={col}
              type="monotone"
              dataKey={col}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  /* ---- Pie chart ---- */
  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={350}>
        <PieChart>
          <Pie
            data={data}
            dataKey={seriesCols[0]}
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={120}
            label={({ name, percent }) =>
              `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
            }
          >
            {data.map((_, i) => (
              <Cell
                key={`cell-${i}`}
                fill={COLORS[i % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "var(--surface-4, #FFFFFF)",
              border: "1px solid var(--border, #E1E4E8)",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return (
    <div className="text-center py-8">
      <p className="text-sm text-[--text-disabled]">
        Unknown chart type: &quot;{chartType}&quot;
      </p>
      <p className="text-xs text-[--text-disabled] mt-1">
        Expected: bar, line, or pie
      </p>
    </div>
  );
}
