import React from 'react';
import { JanusMode, PacketSummaryMessage } from '../types/janus';

type QuickStatsProps = {
  summary?: PacketSummaryMessage;
};

export default function QuickStats({ summary }: QuickStatsProps) {
  if (!summary) {
    return (
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-center">
            <span className="text-xs text-slate-500 italic">No packet data available yet.</span>
        </div>
    );
  }

  const ratio = summary.estimatedRawBytes && summary.bytes > 0
    ? (summary.estimatedRawBytes / summary.bytes).toFixed(1)
    : '-';

  const modeLabel = {
    0: 'Semantic',
    1: 'Text',
    2: 'Morse',
  }[summary.mode];

  return (
    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 space-y-3">
        <div className="flex justify-between items-center">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Last Packet</h3>
            <span className="text-[10px] font-mono text-slate-500">
                {new Date(summary.timestamp).toLocaleTimeString()}
            </span>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
            <div>
                <div className="text-[10px] text-slate-500 uppercase">Size</div>
                <div className="text-lg font-mono text-slate-200">{summary.bytes} B</div>
            </div>
            <div>
                <div className="text-[10px] text-slate-500 uppercase">Compression</div>
                <div className="text-lg font-mono text-green-400">{ratio}x</div>
            </div>
            <div>
                <div className="text-[10px] text-slate-500 uppercase">Mode</div>
                <div className="text-sm font-medium text-blue-300">{modeLabel}</div>
            </div>
            <div>
                 <div className="text-[10px] text-slate-500 uppercase">Raw Est.</div>
                 <div className="text-sm font-mono text-slate-400">{summary.estimatedRawBytes} B</div>
            </div>
        </div>
    </div>
  );
}

