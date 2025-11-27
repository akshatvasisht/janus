import type {
  JanusMode,
  EmotionOverride,
  ConnectionStatus,
  ControlStateUpdate,
} from '@/types/janus';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import PushToTalk from './PushToTalk';
import ModeToggle from './ModeToggle';
import EmotionSelector from './EmotionSelector';
import VoiceCloner from './VoiceCloner';

type ControlPanelProps = {
  status: ConnectionStatus;
  isRecording: boolean;
  isStreaming: boolean;
  mode: JanusMode;
  emotionOverride: EmotionOverride;
  onUpdateControl: (partial: ControlStateUpdate) => void;
};

/**
 * Control surface for recording, streaming mode selection, and emotion override.
 *
 * Optimistically updates UI state and delegates backend synchronization to
 * higher-level hooks supplied via `onUpdateControl`.
 */
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
      <Card>
        <CardContent className="min-h-[240px] flex items-center justify-center">
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
