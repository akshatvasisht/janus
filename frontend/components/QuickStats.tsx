import React from 'react';
import { PacketSummaryMessage } from '../types/janus';

type QuickStatsProps = {
  summary?: PacketSummaryMessage;
};

/**
 * Quick statistics display component for packet information.
 * 
 * Displays metrics from the most recent packet including size, compression ratio,
 * transmission mode, and estimated raw bytes. Shows placeholder message when no
 * packet data is available.
 * 
 * @param props - Component props.
 * @param props.summary - Packet summary message containing statistics to display.
 */
export default function QuickStats({ summary }: QuickStatsProps) {
  if (!summary) {
    return (
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-center">
            <span className="text-xs text-slate-500 italic">No packet data available yet.</span>
        </div>
    );
  }

  const modeLabel = {
    semantic: 'Semantic',
    text_only: 'Text',
    morse: 'Morse',
  }[summary.mode] || 'Unknown';

  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
        <div className="flex justify-between items-center">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Last Packet</h3>
            <span className="text-[10px] font-mono text-slate-500">
                {new Date(summary.created_at_ms).toLocaleTimeString()}
            </span>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
            <div>
                <div className="text-[10px] text-slate-500 uppercase">Size</div>
                <div className="text-lg font-mono text-slate-200">{summary.bytes} B</div>
            </div>
            <div>
                <div className="text-[10px] text-slate-500 uppercase">Mode</div>
                <div className="text-sm font-medium text-blue-300">{modeLabel}</div>
            </div>
        </div>
    </div>
  );
}

