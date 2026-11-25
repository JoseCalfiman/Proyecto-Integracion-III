import { useState } from 'react';
import HistorialView from '../../components/shared/HistorialView';
import Alertas from './Alertas';

export default function Historial() {
  const [tab, setTab] = useState('haccp');

  return (
    <div className="space-y-5">
      <div
        className="flex flex-wrap gap-2"
        role="group"
        aria-label="Tipo de historial"
      >
        {[
          ['haccp', 'Intervenciones HACCP'],
          ['predictions', 'Predicciones y mediciones'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              tab === key
                ? 'bg-green-600 text-white'
                : 'border bg-white text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'haccp' ? <Alertas historial /> : <HistorialView canExport={true} />}
    </div>
  );
}