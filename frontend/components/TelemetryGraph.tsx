"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { PacketSummaryMessage } from '@/types/janus';

interface TelemetryGraphProps {
  packets: PacketSummaryMessage[];
}

export default function TelemetryGraph({ packets }: TelemetryGraphProps) {
  const data = packets.map(p => ({
    time: new Date(p.created_at_ms).toLocaleTimeString(),
    bytes: p.bytes,
    mode: p.mode
  }));

  return (
    <div className="w-full h-64 bg-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-4">
      <h3 className="text-sm font-bold text-black mb-4 uppercase">Bandwidth Usage (Bytes)</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="0" stroke="#e5e5e5" />
          <XAxis dataKey="time" stroke="#000" fontSize={12} tick={{fill: '#000'}} tickFormatter={(val) => val.split(':')[2]} />
          <YAxis stroke="#000" fontSize={12} tick={{fill: '#000'}} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#fff', borderColor: '#000', borderWidth: '2px', boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)' }}
            itemStyle={{ color: '#000', fontWeight: 'bold' }}
            labelStyle={{ color: '#666' }}
          />
          <Line type="step" dataKey="bytes" stroke="#000" strokeWidth={3} dot={false} animationDuration={300} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
