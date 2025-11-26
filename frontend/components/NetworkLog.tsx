"use client";
import { PacketSummaryMessage } from '@/types/janus';

export default function NetworkLog({ packets }: { packets: PacketSummaryMessage[] }) {
  return (
    <div className="w-full h-64 bg-white font-mono text-xs p-4 border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-y-auto">
      <h3 className="text-black font-bold mb-2 sticky top-0 bg-white pb-2 border-b-2 border-black uppercase">Packet Log</h3>
      <div className="space-y-1">
        {packets.slice().reverse().map((p, i) => (
          <div key={i} className="flex gap-4 text-black border-b border-gray-300 pb-1 mb-1 last:border-0">
            <span className="text-gray-500 min-w-[80px]">[{new Date(p.created_at_ms).toLocaleTimeString()}]</span>
            <span className={`min-w-[80px] font-bold ${p.mode === 'semantic' ? 'text-blue-600' : 'text-green-600'}`}>
              {p.mode.toUpperCase()}
            </span>
            <span className="text-black font-bold">{p.bytes} B</span>
          </div>
        ))}
        {packets.length === 0 && (
            <div className="text-gray-500 italic py-4 text-center">No packets transmitted yet...</div>
        )}
      </div>
    </div>
  );
}
