import React from 'react';
import { ConnectionStatus } from '../types/janus';

type HeaderBarProps = {
  status: ConnectionStatus;
  lastError?: string | null;
};

export default function HeaderBar({ status, lastError }: HeaderBarProps) {
  const statusColor = {
    connected: 'bg-green-500',
    connecting: 'bg-amber-500',
    disconnected: 'bg-red-500',
  }[status];

  const statusText = {
    connected: 'Connected',
    connecting: 'Connecting...',
    disconnected: 'Disconnected',
  }[status];

  return (
    <div className="flex items-center justify-between p-4 bg-slate-900/80 border-b border-slate-800 rounded-t-lg backdrop-blur-sm">
      <div>
        <h1 className="text-xl md:text-2xl font-semibold text-slate-50">Janus</h1>
        <p className="text-xs text-slate-400 tracking-wide uppercase">Semantic Audio Codec</p>
      </div>
      
      <div className="flex flex-col items-end gap-1">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800">
          <div className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
          <span className="text-xs font-medium text-slate-300">{statusText}</span>
        </div>
        {lastError && (
          <span className="text-xs text-red-400 max-w-[200px] truncate" title={lastError}>
            {lastError}
          </span>
        )}
      </div>
    </div>
  );
}

