'use client';

interface RiskBadgeProps {
  risk: 'low' | 'medium' | 'high';
  label?: string;
}

export default function RiskBadge({ risk, label }: RiskBadgeProps) {
  const colors = {
    low: 'bg-green-100 text-green-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800',
  };

  const displayLabel = label || risk.charAt(0).toUpperCase() + risk.slice(1);

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[risk]}`}>
      {displayLabel}
    </span>
  );
}
