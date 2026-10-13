import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const ConsumptionForecastChart = () => {
  // Datos de ejemplo: histórico + pronóstico
    // datos viene desde el padre (Ahorro.jsx)
  const data = [
    { date: 'Oct 2', historico: 450, pronostico: null },
    { date: 'Oct 3', historico: 420, pronostico: null },
    { date: 'Oct 4', historico: 480, pronostico: null },
    { date: 'Oct 5', historico: 420, pronostico: null },
    { date: 'Oct 6', historico: 380, pronostico: null },
    { date: 'Oct 7', historico: 375, pronostico: 375 },
    { date: 'Oct 8', historico: null, pronostico: 360 },
    { date: 'Oct 9', historico: null, pronostico: 340 },
    { date: 'Oct 10', historico: null, pronostico: 320 },
    { date: 'Oct 11', historico: null, pronostico: 310 },
    { date: 'Oct 12', historico: null, pronostico: 300 },
    { date: 'Oct 13', historico: null, pronostico: 280 },
  ];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 11 }} />
        <YAxis
          stroke="#9ca3af"
          tick={{ fontSize: 11 }}
          label={{ value: 'kWh', angle: -90, position: 'insideLeft', fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        />
        <Line
          type="monotone"
          dataKey="historico"
          stroke="#10b981"
          strokeWidth={2.5}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="pronostico"
          stroke="#f59e0b"
          strokeWidth={2.5}
          strokeDasharray="5 5"
          dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default ConsumptionForecastChart;