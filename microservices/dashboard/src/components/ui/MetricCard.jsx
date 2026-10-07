import React from 'react';

const MetricCard = ({ title, value, unit, icon: Icon, color = 'green', borderColor }) => {
  const colorClasses = {
    green: 'text-green-600 bg-green-50',
    red: 'text-red-600 bg-red-50',
    yellow: 'text-yellow-600 bg-yellow-50',
    blue: 'text-blue-600 bg-blue-50',
  };

  // Si value es undefined, null o NaN, mostramos 0
  const displayValue = value === undefined || value === null || Number.isNaN(value)
    ? 0
    : value;

  return (
    <div className={`bg-white p-6 rounded-lg shadow-md ${borderColor || ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
            {title}
          </p>
          <div className="flex items-baseline gap-1 mt-2">
            <p className="text-4xl font-bold text-gray-800">{displayValue}</p>
            {unit && <p className="text-lg text-gray-500">{unit}</p>}
          </div>
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;