'use client';

import { useCallback, useState } from 'react';
import { useJanusWebSocket } from './useJanusWebSocket';
import type {
  JanusMode,
  EmotionOverride,
  TranscriptMessage,
  PacketSummaryMessage,
  ConnectionStatus,
} from '../types/janus';

// Helper to convert frontend mode (string) to number for UI compatibility
const modeToNumber = (mode: JanusMode): 0 | 1 | 2 => {
  switch (mode) {
    case 'semantic':
      return 0;
    case 'text_only':
      return 1;
    case 'morse':
      return 2;
    default:
      return 0;
  }
};

const numberToMode = (num: 0 | 1 | 2): JanusMode => {
  switch (num) {
    case 0:
      return 'semantic';
    case 1:
      return 'text_only';
    case 2:
      return 'morse';
    default:
      return 'semantic';
  }
};

export type JanusSocketState = {
  status: ConnectionStatus;
  mode: 0 | 1 | 2; // Keep as number for UI compatibility
  emotionOverride: EmotionOverride;
  isRecording: boolean;
  isStreaming: boolean;
  transcripts: TranscriptMessage[];
  lastPacketSummary?: PacketSummaryMessage;
  lastError?: string | null;
  sendControl: (
    control: Partial<{
      mode?: 0 | 1 | 2;
      emotionOverride?: EmotionOverride;
      isRecording?: boolean;
      isStreaming?: boolean;
    }>
  ) => void;
};

export function useJanusSocket(): JanusSocketState {
  const [mode, setMode] = useState<0 | 1 | 2>(0);
  const [emotionOverride, setEmotionOverride] =
    useState<EmotionOverride>('auto');
  const [isRecording, setIsRecording] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const {
    connectionStatus,
    transcripts,
    lastPacket,
    sendControl: sendControlRaw,
    isConnected,
  } = useJanusWebSocket();

  const sendControl = useCallback(
    (
      partial: Partial<{
        mode?: 0 | 1 | 2;
        emotionOverride?: EmotionOverride;
        isRecording?: boolean;
        isStreaming?: boolean;
      }>
    ) => {
      // Update local state immediately for UI responsiveness
      if (partial.mode !== undefined) setMode(partial.mode);
      if (partial.emotionOverride !== undefined)
        setEmotionOverride(partial.emotionOverride);
      if (partial.isRecording !== undefined)
        setIsRecording(partial.isRecording);
      if (partial.isStreaming !== undefined)
        setIsStreaming(partial.isStreaming);

      // Send to backend via WebSocket
      if (isConnected) {
        sendControlRaw({
          mode:
            partial.mode !== undefined ? numberToMode(partial.mode) : undefined,
          emotion_override: partial.emotionOverride,
          is_recording: partial.isRecording,
          is_streaming: partial.isStreaming,
        });
      }
    },
    [isConnected, sendControlRaw]
  );

  return {
    status: connectionStatus,
    mode,
    emotionOverride,
    isRecording,
    isStreaming,
    transcripts,
    lastPacketSummary: lastPacket || undefined,
    lastError: connectionStatus === 'disconnected' ? 'Connection lost' : null,
    sendControl,
  };
}
