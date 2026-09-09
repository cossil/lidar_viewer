import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface Plots2DProps {
  sweepData?: {
    distances: number[];
    p_detected: number[];
    p_reliable?: number[];
    p_characterized?: number[];
    expected_returns?: number[];
    range_uncertainty?: number[];
  };
  heatmapData?: {
    dbh_values: number[]; // in cm or m
    distances: number[];
    z_matrix: number[][]; // P_d values
  };
}

export const Plots2D: React.FC<Plots2DProps> = ({ sweepData, heatmapData }) => {
  const curvePlotRef = useRef<HTMLDivElement>(null);
  const heatmapPlotRef = useRef<HTMLDivElement>(null);

  // Default synthetic curve if no data provided
  const defaultDistances = Array.from({ length: 40 }, (_, i) => 2 + i * 2); // 2m to 80m
  const distances = sweepData?.distances || defaultDistances;
  const p_det =
    sweepData?.p_detected ||
    distances.map((d) => Math.max(0, Math.min(1, 1 / (1 + Math.exp(0.12 * (d - 45))))));
  const p_rel =
    sweepData?.p_reliable ||
    distances.map((d) => Math.max(0, Math.min(1, 1 / (1 + Math.exp(0.15 * (d - 38))))));
  const p_char =
    sweepData?.p_characterized ||
    distances.map((d) => Math.max(0, Math.min(1, 1 / (1 + Math.exp(0.18 * (d - 30))))));
  const returns =
    sweepData?.expected_returns ||
    distances.map((d) => Math.round(180 / ((d / 10) * (d / 10))));

  useEffect(() => {
    if (!curvePlotRef.current) return;

    const traces: Plotly.Data[] = [
      {
        x: distances,
        y: p_det,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'P(Detected)',
        line: { color: '#06b6d4', width: 3 },
        marker: { size: 6 },
      },
      {
        x: distances,
        y: p_rel,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'P(Reliable, N≥5)',
        line: { color: '#10b981', width: 2.5, dash: 'dot' },
        marker: { size: 5 },
      },
      {
        x: distances,
        y: p_char,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'P(Characterized, N≥10 & Cg≥30%)',
        line: { color: '#6366f1', width: 2.5, dash: 'dash' },
        marker: { size: 5 },
      },
      {
        x: distances,
        y: returns.map((r) => r / 100), // scaled secondary axis
        type: 'scatter',
        mode: 'lines',
        name: 'Expected Returns (scaled)',
        yaxis: 'y2',
        line: { color: '#f59e0b', width: 2 },
      },
    ];

    const layout: Partial<Plotly.Layout> = {
      title: {
        text: 'Detection & Classification Probabilities vs. Target Distance',
        font: { color: '#f8fafc', size: 14, family: 'Inter, sans-serif' },
      },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'rgba(15, 23, 42, 0.4)',
      margin: { l: 50, r: 50, t: 45, b: 45 },
      xaxis: {
        title: { text: 'Distance R (m)', font: { color: '#94a3b8' } },
        color: '#94a3b8',
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      yaxis: {
        title: { text: 'Probability (0 - 1.0)', font: { color: '#94a3b8' } },
        range: [0, 1.05],
        color: '#94a3b8',
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      yaxis2: {
        title: { text: 'Expected Returns / 100', font: { color: '#f59e0b' } },
        overlaying: 'y',
        side: 'right',
        color: '#f59e0b',
        showgrid: false,
      },
      legend: {
        orientation: 'h',
        x: 0,
        y: 1.15,
        font: { color: '#e2e8f0', size: 11 },
      },
    };

    Plotly.newPlot(curvePlotRef.current, traces, layout, { responsive: true, displayModeBar: false });
  }, [distances, p_det, p_rel, p_char, returns]);

  useEffect(() => {
    if (!heatmapPlotRef.current) return;

    // Generate or use heatmap matrix
    const dbhArr = heatmapData?.dbh_values || [5, 10, 15, 20, 30, 40, 50]; // cm
    const distArr = heatmapData?.distances || [10, 20, 30, 40, 50, 60, 70]; // m
    const zMat: number[][] =
      heatmapData?.z_matrix ||
      dbhArr.map((dbh) =>
        distArr.map((r) => {
          const val = Math.min(1.0, (dbh / 20) * (50 / r));
          return Math.round(val * 100) / 100;
        })
      );

    const heatTrace: Plotly.Data[] = [
      {
        z: zMat,
        x: distArr,
        y: dbhArr,
        type: 'heatmap',
        colorscale: 'Viridis',
        colorbar: {
          title: { text: 'P(Det)', font: { color: '#94a3b8', size: 11 } },
          tickfont: { color: '#cbd5e1' },
        },
      },
    ];

    const heatLayout: Partial<Plotly.Layout> = {
      title: {
        text: 'DBH vs. Distance Detection Heatmap (PRD §44 / §50)',
        font: { color: '#f8fafc', size: 14, family: 'Inter, sans-serif' },
      },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'rgba(15, 23, 42, 0.4)',
      margin: { l: 50, r: 50, t: 45, b: 45 },
      xaxis: {
        title: { text: 'Distance (m)', font: { color: '#94a3b8' } },
        color: '#94a3b8',
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
      yaxis: {
        title: { text: 'Trunk DBH (cm)', font: { color: '#94a3b8' } },
        color: '#94a3b8',
        gridcolor: 'rgba(255, 255, 255, 0.05)',
      },
    };

    Plotly.newPlot(heatmapPlotRef.current, heatTrace, heatLayout, { responsive: true, displayModeBar: false });
  }, [heatmapData]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div className="glass-panel p-5">
        <div ref={curvePlotRef} className="w-full h-80" />
      </div>

      <div className="glass-panel p-5">
        <div ref={heatmapPlotRef} className="w-full h-80" />
      </div>
    </div>
  );
};
