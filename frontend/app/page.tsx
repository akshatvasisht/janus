'use client';

import React from 'react';
import { useJanusSocket } from '../hooks/useJanusSocket';
import HeaderBar from '../components/HeaderBar';
import ControlPanel from '../components/ControlPanel';
import ConversationPanel from '../components/ConversationPanel';

export default function DashboardPage() {
  const {
    status,
    lastError,
    mode,
    emotionOverride,
    isRecording,
    isStreaming,
    transcripts,
    lastPacketSummary,
    sendControl,
  } = useJanusSocket();

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      {/* Main content */}
      <div className="relative z-10">
        <main className="min-h-screen font-sans">
          <div className="container mx-auto px-6 py-8 space-y-6 flex flex-col">
            {/* Header */}
            <HeaderBar
              status={status}
              lastError={lastError}
              links={[{ href: '/telemetry', label: 'Telemetry' }]}
            />

            {/* Main Content Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
              {/* Left Column: Controls */}
              <div className="flex flex-col gap-6 lg:col-span-1">
                <ControlPanel
                  status={status}
                  isRecording={isRecording}
                  isStreaming={isStreaming}
                  mode={mode}
                  emotionOverride={emotionOverride}
                  lastPacketSummary={lastPacketSummary}
                  onUpdateControl={sendControl}
                />

                {/* TODO: Remove this footer note when real backend integration is complete */}
                <div className="mt-auto pt-6 text-[10px] text-muted-foreground text-center pb-4">
                  Janus Project • Dashboard v1.0 • Mock Mode Active
                </div>
              </div>

              {/* Right Column: Conversation */}
              <div className="h-full min-h-[500px] lg:col-span-3">
                <ConversationPanel transcripts={transcripts} />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
