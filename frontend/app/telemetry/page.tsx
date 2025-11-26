'use client';

import React, { useMemo } from 'react';
import TelemetryGraph from '@/components/TelemetryGraph';
import NetworkLog from '@/components/NetworkLog';
import { useJanusWebSocket } from '@/hooks/useJanusWebSocket';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import HeaderBar from '@/components/HeaderBar';

export default function TelemetryPage() {
  const { packetHistory, connectionStatus, lastPacket } = useJanusWebSocket();

  const { totalBytes, totalPackets } = useMemo(() => {
    const counts = packetHistory.reduce(
      (acc, pkt) => {
        acc.totalBytes += pkt.bytes;
        acc.totalPackets += 1;
        return acc;
      },
      { totalBytes: 0, totalPackets: 0 }
    );
    return counts;
  }, [packetHistory]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="container mx-auto px-6 py-8 space-y-6">
        <HeaderBar
          status={connectionStatus}
          lastError={connectionStatus === 'disconnected' ? 'Connection lost' : undefined}
          links={[{ href: '/', label: 'Dashboard' }]}
        />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Bandwidth</CardTitle>
              <CardDescription>
                Packets over time (live from backend)
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4">
              <TelemetryGraph packets={packetHistory} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <CardDescription>Rolling metrics</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  Total packets
                </span>
                <span className="font-mono text-lg">{totalPackets}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  Total bytes
                </span>
                <span className="font-mono text-lg">{totalBytes}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  Last packet
                </span>
                <span className="font-mono text-lg">
                  {lastPacket ? `${lastPacket.bytes} B` : '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">Mode</span>
                <span className="font-semibold uppercase">
                  {lastPacket ? lastPacket.mode : '—'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Packet Log</CardTitle>
            <CardDescription>Newest first</CardDescription>
          </CardHeader>
          <CardContent className="p-4">
            <NetworkLog packets={packetHistory} />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
