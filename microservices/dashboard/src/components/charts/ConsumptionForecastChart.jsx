import React from 'react';
import { useFetch } from '../../hooks/useApi';
import { getForecast } from '../../api/optimizacion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const ConsumptionForecastChart = () => {
  const { data, loading, error } = useFetch(getForecast);

  if (loading) return <p className="text-sm text-gray-500">Cargando pronóstico...</p>;
  if (error) return <p role="alert" className="text-sm text-red-600">{error}</p>;
  if (!data?.length) return <p className="text-sm text-gray-500">Aún no hay pronósticos disponibles.</p>;

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