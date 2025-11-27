'use client';

import { useMemo } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PacketSummaryMessage } from '@/types/janus';

interface TelemetryGraphProps {
  packets: PacketSummaryMessage[];
}

type TelemetryPoint = {
  time: string;
  bytes: number;
  mode: PacketSummaryMessage['mode'];
};

/**
 * Renders packet byte counts over time using Recharts.
 */
export default function TelemetryGraph({ packets }: TelemetryGraphProps) {
  const data = useMemo<TelemetryPoint[]>(
    () =>
      packets.map((packet) => ({
        time: new Date(packet.created_at_ms).toLocaleTimeString(),
        bytes: packet.bytes,
        mode: packet.mode,
      })),
    [packets]
  );

  const formatTick = (value: string): string => value.split(':')[2] ?? value;
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="0" stroke="#e5e5e5" />
          <XAxis
            dataKey="time"
            stroke="#000"
            fontSize={12}
            tick={{ fill: '#000' }}
            tickFormatter={formatTick}
          />
          <YAxis stroke="#000" fontSize={12} tick={{ fill: '#000' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              borderColor: '#000',
              borderWidth: '2px',
              boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)',
            }}
            itemStyle={{ color: '#000', fontWeight: 'bold' }}
            labelStyle={{ color: '#666' }}
          />
          <Line
            type="step"
            dataKey="bytes"
            stroke="#000"
            strokeWidth={3}
            dot={false}
            animationDuration={300}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
