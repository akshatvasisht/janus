import React from 'react';
import {
  JanusMode,
  EmotionOverride,
  PacketSummaryMessage,
  ConnectionStatus,
} from '../types/janus';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
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
  onUpdateControl: (partial: {
    isRecording?: boolean;
    isStreaming?: boolean;
    mode?: JanusMode;
    emotionOverride?: EmotionOverride;
  }) => void;
};

export default function ControlPanel({
  status,
  isRecording,
  isStreaming,
  mode,
  emotionOverride,
  onUpdateControl,
}: ControlPanelProps) {
  const isConnected = status === 'connected';

  return (
    <div className="space-y-6">
      {/* PTT Button Card */}
      <Card>
        <CardContent className="pt-6 flex flex-col items-center justify-center">
          <PushToTalk
            isRecording={isRecording}
            isStreaming={isStreaming}
            disabled={!isConnected}
            onHoldStart={() => onUpdateControl({ isRecording: true })}
            onHoldEnd={() => onUpdateControl({ isRecording: false })}
            onToggleStreaming={() =>
              onUpdateControl({ isStreaming: !isStreaming })
            }
          />
        </CardContent>
      </Card>

      {/* Mode Selector Card */}
      <Card>
        <CardHeader>
          <CardTitle>Mode Selector</CardTitle>
        </CardHeader>
        <CardContent>
          <ModeToggle
            mode={mode}
            onChange={(m) => onUpdateControl({ mode: m })}
            isMorseEnabled
          />
        </CardContent>
      </Card>

      {/* Emotion Override Card */}
      <Card>
        <CardHeader>
          <CardTitle>Emotion Override</CardTitle>
        </CardHeader>
        <CardContent>
          <EmotionSelector
            value={emotionOverride}
            onChange={(v) => onUpdateControl({ emotionOverride: v })}
          />
        </CardContent>
      </Card>

      {/* Voice Cloner Card (kept from current branch) */}
      <Card>
        <CardHeader>
          <CardTitle>Voice Cloning</CardTitle>
        </CardHeader>
        <CardContent>
          <VoiceCloner disabled={!isConnected} />
        </CardContent>
      </Card>

    </div>
  );
}
