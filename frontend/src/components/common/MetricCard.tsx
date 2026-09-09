import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  status?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  thresholdText?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  status = 'neutral',
  thresholdText,
}) => {
  const statusStyles = {
    success: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
    warning: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
    danger: 'border-rose-500/30 text-rose-400 bg-rose-500/10',
    info: 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10',
    neutral: 'border-white/10 text-slate-200 bg-slate-800/40',
  };

  return (
    <div className="glass-panel p-4 flex flex-col justify-between space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {thresholdText && (
          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${statusStyles[status]}`}>
            {thresholdText}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-extrabold font-mono-val text-white tracking-tight">
          {value}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>

      {subtext && <p className="text-[11px] text-slate-400">{subtext}</p>}
    </div>
  );
};
