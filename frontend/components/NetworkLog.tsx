'use client';

import { useMemo } from 'react';
import type { PacketSummaryMessage } from '@/types/janus';

interface NetworkLogProps {
  packets: PacketSummaryMessage[];
}

const formatTimestamp = (timestampMs: number): string =>
  new Date(timestampMs).toLocaleTimeString();

/**
 * Packet log showing most recent events first.
 */
export default function NetworkLog({ packets }: NetworkLogProps) {
  const entries = useMemo<PacketSummaryMessage[]>(
    () => [...packets].reverse(),
    [packets]
  );

  return (
    <div className="w-full h-64 bg-white font-mono text-xs p-4 border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-y-auto">
      <h3 className="text-black font-bold mb-2 sticky top-0 bg-white pb-2 border-b-2 border-black uppercase">
        Packet Log
      </h3>
      <div className="space-y-1">
        {entries.map((packet, index) => (
          <div
            key={`${packet.created_at_ms}-${packet.bytes}-${index}`}
            className="flex gap-4 text-black border-b border-gray-300 pb-1 mb-1 last:border-0"
          >
            <span className="text-gray-500 min-w-[80px]">
              [{formatTimestamp(packet.created_at_ms)}]
            </span>
            <span
              className={`min-w-[80px] font-bold ${packet.mode === 'semantic' ? 'text-blue-600' : 'text-green-600'}`}
            >
              {packet.mode.toUpperCase()}
            </span>
            <span className="text-black font-bold">{packet.bytes} B</span>
          </div>
        ))}
        {entries.length === 0 && (
          <div className="text-gray-500 italic py-4 text-center">
            No packets transmitted yet.
          </div>
        )}
      </div>
    </div>
  );
}
