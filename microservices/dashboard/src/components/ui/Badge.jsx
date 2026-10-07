import React from 'react';

const styles = {
  green: 'bg-green-100 text-green-700',
  red: 'bg-red-100 text-red-700',
  yellow: 'bg-yellow-100 text-yellow-700',
  blue: 'bg-blue-100 text-blue-700',
  gray: 'bg-gray-100 text-gray-600',
};

const Badge = ({ children, color = 'gray' }) => (
  <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${styles[color] || styles.gray}`}>
    {children}
  </span>
);

export default Badge;
