import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
const valido = (valor) => typeof valor === 'number' && Number.isFinite(valor);

// No se generan lecturas de ejemplo. Los intervalos sin medición quedan vacíos.
const TemperatureChart = ({ data = [], series = [], labels = {}, minTemp, maxTemp, loading = false }) => {
  const tieneLecturas = data.some((punto) => series.some((key) => valido(punto[key])));
  const dominio = data.length ? [data[0].timestamp, data[data.length - 1].timestamp] : ['auto', 'auto'];
  const hora = (ms) => new Date(ms).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false });

  return (
    <section className="min-w-0 rounded-lg bg-white p-4 shadow-md sm:p-6" aria-label="Evolución de temperatura">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-700">Evolución de Temperatura (Últimas 2h)</h2>
          <p className="mt-1 text-xs text-gray-500">Promedios por intervalos de 2 minutos · °C · Sin interpolación de lecturas ausentes</p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-gray-600">
          {valido(maxTemp) && <span className="flex items-center gap-1"><span className="w-4 border-t-2 border-dashed border-red-500" />Máximo HACCP: {maxTemp} °C</span>}
          {valido(minTemp) && <span className="flex items-center gap-1"><span className="w-4 border-t-2 border-dashed border-blue-500" />Mínimo HACCP: {minTemp} °C</span>}
        </div>
      </div>
      {loading ? <div className="flex h-[300px] items-center justify-center text-sm text-gray-500" role="status">Consultando temperaturas…</div>
        : !tieneLecturas ? <div className="flex h-[300px] items-center justify-center text-sm text-gray-500">Sin lecturas disponibles para esta selección.</div>
        : <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="timestamp" type="number" scale="time" domain={dominio} tickFormatter={hora} stroke="#9ca3af" minTickGap={35} />
              <YAxis stroke="#9ca3af" domain={['auto', 'auto']} tickFormatter={(v) => `${v}°C`} />
              <Tooltip labelFormatter={(ms) => new Date(ms).toLocaleString('es-CL')} formatter={(value, name) => [`${Number(value).toLocaleString('es-CL', { maximumFractionDigits: 2 })} °C`, name]} contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }} />
              <Legend />
              {valido(maxTemp) && <ReferenceLine y={maxTemp} stroke="#ef4444" strokeDasharray="5 5" ifOverflow="extendDomain" />}
              {valido(minTemp) && <ReferenceLine y={minTemp} stroke="#3b82f6" strokeDasharray="5 5" ifOverflow="extendDomain" />}
              {series.map((key, i) => <Line key={key} name={labels[key] || key} type="linear" dataKey={key} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>}
    </section>
  );
};

export default TemperatureChart;