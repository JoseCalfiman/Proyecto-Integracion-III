// graficos de temperatura de los ultimos 2 horas, con recharts

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = [
  "#10b981",
  "#3b82f6",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
];

const SAMPLE = [
  { time: "-120s", temp: -2.5 },
  { time: "-90s", temp: -2.3 },
  { time: "-60s", temp: -2.8 },
  { time: "-30s", temp: -1.5 },
  { time: "now", temp: 2.5 },
];

const TemperatureChart = ({ data, series }) => {
  const isReal = Array.isArray(data);
  const chartData = isReal ? data : SAMPLE;
  const lines = isReal && series?.length ? series : ["temp"];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-700">
          Evolución de Temperatura (Últimas 2h)
        </h2>
        <div className="flex items-center gap-2 text-sm">
          <span className="w-4 h-0.5 bg-red-500"></span>
          <span className="text-gray-600">Límite (4°C)</span>
        </div>
      </div>

      {isReal && chartData.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-sm text-gray-400">
          Sin lecturas en las últimas 2 horas. ¿Está corriendo el simulador /
          ESP32?
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="time" stroke="#9ca3af" minTickGap={30} />
            <YAxis
              stroke="#9ca3af"
              domain={isReal ? ["auto", "auto"] : [-6, 6]}
              tickFormatter={(v) => `${v}°C`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
              formatter={(value, name) => [
                `${value}°C`,
                name === "temp" ? "Temperatura" : name,
              ]}
            />
            {isReal && <Legend />}
            <ReferenceLine
              y={4}
              stroke="#ef4444"
              strokeDasharray="5 5"
              strokeWidth={2}
              ifOverflow="extendDomain"
            />
            {lines.map((key, i) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6 }}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default TemperatureChart;