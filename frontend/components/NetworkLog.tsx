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
    <div className="w-full h-64 font-mono text-xs overflow-y-auto">
      <div className="space-y-1">
        {entries.map((packet, index) => (
          <div
            key={`${packet.created_at_ms}-${packet.bytes}-${index}`}
            className="flex gap-4 text-foreground border-b border-border/40 pb-1 mb-1 last:border-0"
          >
            <span className="text-muted-foreground min-w-[80px]">
              [{formatTimestamp(packet.created_at_ms)}]
            </span>
            <span
              className={`min-w-[80px] font-bold ${packet.mode === 'semantic' ? 'text-blue-700' : 'text-green-700'}`}
            >
              {packet.mode.toUpperCase()}
            </span>
            <span className="text-foreground font-bold">{packet.bytes} B</span>
            {packet.emotion ? (
              <span className="text-foreground font-medium truncate">
                {packet.emotion}
              </span>
            ) : null}
            {packet.snippet ? (
              <span className="text-muted-foreground truncate max-w-[240px]">
                “{packet.snippet}”
              </span>
            ) : null}
          </div>
        ))}
        {entries.length === 0 && (
          <div className="text-muted-foreground italic py-4 text-center">
            No packets in history. Transmissions appear here.
          </div>
        )}
      </div>
    </div>
  );
}
