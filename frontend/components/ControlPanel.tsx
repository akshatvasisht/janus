import React from 'react';
import { JanusMode, EmotionOverride, PacketSummaryMessage, ConnectionStatus } from '../types/janus';
import PushToTalk from './PushToTalk';
import ModeToggle from './ModeToggle';
import EmotionSelector from './EmotionSelector';
import QuickStats from './QuickStats';
import VoiceCloner from './VoiceCloner';

type ControlPanelProps = {
  status: ConnectionStatus;
  isRecording: boolean;
  isStreaming: boolean;
  mode: JanusMode;
  emotionOverride: EmotionOverride;
  lastPacketSummary?: PacketSummaryMessage;
  onUpdateControl: (partial: {
    isRecording?: boolean;
    isStreaming?: boolean;
    mode?: JanusMode;
    emotionOverride?: EmotionOverride;
  }) => void;
};

/**
 * Main control panel component for Janus interface.
 * 
 * Provides controls for push-to-talk interaction, transmission mode selection,
 * emotion override settings, and voice cloning. Displays packet statistics
 * and manages connection state.
 * 
 * @param props - Component props.
 * @param props.status - Current WebSocket connection status.
 * @param props.isRecording - Whether recording is currently active.
 * @param props.isStreaming - Whether streaming mode is enabled.
 * @param props.mode - Currently selected transmission mode.
 * @param props.emotionOverride - Currently selected emotion override setting.
 * @param props.lastPacketSummary - Most recent packet summary for statistics display.
 * @param props.onUpdateControl - Callback invoked when control settings change.
 */
export default function ControlPanel({
  status,
  isRecording,
  isStreaming,
  mode,
  emotionOverride,
  lastPacketSummary,
  onUpdateControl,
}: ControlPanelProps) {
  
  const isConnected = status === 'connected';

  return (
    <div className="flex flex-col gap-6">
        {/* PTT Section */}
        <section className="bg-slate-900/50 rounded-xl p-6 border border-slate-800 flex flex-col items-center">
             <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide w-full text-left mb-6">
                Talk to Janus
             </h2>
             <PushToTalk 
                isRecording={isRecording}
                isStreaming={isStreaming}
                disabled={!isConnected}
                onHoldStart={() => onUpdateControl({ isRecording: true })}
                onHoldEnd={() => onUpdateControl({ isRecording: false })}
                onToggleStreaming={() => onUpdateControl({ isStreaming: !isStreaming })}
             />
        </section>

        {/* Controls Group */}
        <section className="grid gap-4 bg-slate-900/50 rounded-xl p-6 border border-slate-800">
            <div className="space-y-3">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Mode</h2>
                <ModeToggle 
                    mode={mode} 
                    onChange={(m) => onUpdateControl({ mode: m })} 
                    isMorseEnabled={true}
                />
            </div>

            <div className="space-y-3 pt-4 border-t border-slate-800">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Emotion Override</h2>
                <EmotionSelector 
                    value={emotionOverride}
                    onChange={(v) => onUpdateControl({ emotionOverride: v })}
                />
            </div>

            <div className="space-y-3 pt-4 border-t border-slate-800">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Voice Cloning</h2>
                <VoiceCloner disabled={!isConnected} />
            </div>
        </section>

        {/* Stats */}
        <QuickStats summary={lastPacketSummary} />
    </div>
  );
}

