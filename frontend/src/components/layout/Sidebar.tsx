import React from 'react';
import {
  LayoutDashboard,
  Cpu,
  Layers,
  PlayCircle,
  BarChart3,
  FileText,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'sensors' | 'scenarios' | 'simulations' | 'visualizations' | 'reports';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard, badge: null },
    { id: 'sensors' as NavTab, label: 'Sensor Library', icon: Cpu, badge: 'PRD §47.2' },
    { id: 'scenarios' as NavTab, label: 'Scenario Builder', icon: Layers, badge: 'PRD §48' },
    { id: 'simulations' as NavTab, label: 'Simulations', icon: PlayCircle, badge: 'MC/3-Mode' },
    { id: 'visualizations' as NavTab, label: '2D & 3D Viz', icon: BarChart3, badge: 'Phase 12' },
    { id: 'reports' as NavTab, label: 'Reports & Export', icon: FileText, badge: '14 Secs' },
  ];

  return (
    <aside className="w-64 border-r border-white/10 bg-slate-900/50 backdrop-blur-md p-4 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-500/20 to-indigo-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-white/5">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-3.5 rounded-xl bg-slate-800/40 border border-white/5 space-y-2">
        <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          Reproducible Physics
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Seeded RNG, immutable versioned sensors, SI units internally, no fabricated detection probabilities.
        </p>
      </div>
    </aside>
  );
};
