'use client';

import React from 'react';
import { useJanusSocket } from '../hooks/useJanusSocket';
import HeaderBar from '../components/HeaderBar';
import ControlPanel from '../components/ControlPanel';
import ConversationPanel from '../components/ConversationPanel';

/**
 * Main page component for the Janus application interface.
 * 
 * Provides the primary user interface for push-to-talk interaction, transmission
 * mode selection, and real-time transcript visualization. Manages WebSocket connection
 * state and coordinates between control panel and conversation display components.
 */
export default function MissionControlPage() {
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
    <main className="min-h-screen bg-slate-950 text-slate-50 font-sans selection:bg-blue-500/30">
      <div className="mx-auto max-w-6xl px-4 py-6 space-y-6 h-screen flex flex-col">
        {/* Header */}
        <HeaderBar status={status} lastError={lastError} />

        {/* Main Content Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
          {/* Left Column: Controls (Fixed width on large screens) */}
          <div className="lg:col-span-5 xl:col-span-4 flex flex-col gap-6 overflow-y-auto">
            <ControlPanel
              status={status}
              isRecording={isRecording}
              isStreaming={isStreaming}
              mode={mode}
              emotionOverride={emotionOverride}
              lastPacketSummary={lastPacketSummary}
              onUpdateControl={sendControl}
            />
          </div>

          {/* Right Column: Conversation (Expands) */}
          <div className="lg:col-span-7 xl:col-span-8 h-full min-h-[500px]">
            <ConversationPanel transcripts={transcripts} />
          </div>
        </div>
      </div>
    </main>
  );
}
