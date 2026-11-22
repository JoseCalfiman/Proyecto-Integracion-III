import React from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const formato = (n) => n.toLocaleString("es-CL", {
  minimumFractionDigits: 1, maximumFractionDigits: 1,
});

const ConsumptionChart = ({ data = [], loading = false }) => {
  // Solo datos provenientes del backend: nunca inventar puntos de ejemplo.
  const registros = Array.isArray(data) ? data.filter((d) => Number.isFinite(Number(d.kwh))) : [];
  const total = registros.reduce((suma, punto) => suma + Number(punto.kwh), 0);
  const promedio = registros.length ? total / registros.length : 0;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-700">Tendencia de consumo energético (7 días)</h2>
          <p className="text-xs text-gray-500">Energía diaria registrada en la planta</p>
        </div>
        {registros.length > 0 && (
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <p className="text-xs text-gray-500">TOTAL DEL PERIODO</p>
              <p className="text-lg font-bold text-green-600">{formato(total)} kWh</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">PROMEDIO DIARIO</p>
              <p className="text-lg font-bold text-green-600">{formato(promedio)} kWh</p>
            </div>
          </div>
        )}
      </div>
      {loading && registros.length === 0 ? (
        <div className="h-[250px] flex items-center justify-center text-sm text-gray-500">Cargando consumo real…</div>
      ) : registros.length === 0 ? (
        <div className="h-[250px] flex items-center justify-center text-sm text-gray-500">Sin datos de consumo disponibles.</div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={registros}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="day" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" tickFormatter={(v) => `${v} kWh`} />
            <Tooltip formatter={(value) => [`${formato(Number(value))} kWh`, "Consumo"]} />
            <Line type="monotone" dataKey="kwh" stroke="#10b981" strokeWidth={3} dot={{ fill: "#10b981", r: 4 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default ConsumptionChart;