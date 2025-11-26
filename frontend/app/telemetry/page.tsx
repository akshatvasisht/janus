'use client';
import { useEffect, useState } from 'react';
import { useJanusSocket } from '@/hooks/useJanusSocket';
import TelemetryGraph from '@/components/TelemetryGraph';
import NetworkLog from '@/components/NetworkLog';
import HeaderBar from '@/components/HeaderBar';
import { PacketSummaryMessage } from '@/types/janus';

export default function TelemetryPage() {
  const { lastPacketSummary, status, lastError } = useJanusSocket();
  const [packets, setPackets] = useState<PacketSummaryMessage[]>([]);

  useEffect(() => {
    if (lastPacketSummary) {
      setPackets((prev) => {
        // Avoid duplicates based on timestamp if needed, but assuming stream is unique
        return [...prev, lastPacketSummary].slice(-50); // Keep last 50
      });
    }
  }, [lastPacketSummary]);

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <div className="relative z-10">
        <main className="min-h-screen font-sans">
          <div className="container mx-auto px-6 py-8 space-y-6 flex flex-col">
            <HeaderBar
              status={status}
              lastError={lastError}
              links={[{ href: '/', label: 'Dashboard' }]}
            />
            <div className="max-w-4xl mx-auto w-full space-y-8">
              <div className="grid gap-6">
                <TelemetryGraph packets={packets} />
                <NetworkLog packets={packets} />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
