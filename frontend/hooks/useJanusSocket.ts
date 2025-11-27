'use client';

import { useCallback, useState } from 'react';
import { useJanusWebSocket } from './useJanusWebSocket';
import type {
  JanusMode,
  EmotionOverride,
  TranscriptMessage,
  PacketSummaryMessage,
  ConnectionStatus,
  ControlStateUpdate,
} from '@/types/janus';
export type JanusSocketState = {
  status: ConnectionStatus;
  mode: JanusMode;
  emotionOverride: EmotionOverride;
  isRecording: boolean;
  isStreaming: boolean;
  transcripts: TranscriptMessage[];
  lastPacketSummary?: PacketSummaryMessage;
  lastError?: string | null;
  sendControl: (control: ControlStateUpdate) => void;
};

/**
 * Combines WebSocket connectivity with local UI state for Janus controls.
 *
 * Maintains optimistic UI state for recording/streaming/mode while delegating
 * network synchronization to the underlying WebSocket hook.
 */
export function useJanusSocket(): JanusSocketState {
  const [mode, setMode] = useState<JanusMode>('semantic');
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
    (partial: ControlStateUpdate) => {
      if (partial.mode !== undefined) {
        setMode(partial.mode);
      }
      if (partial.emotionOverride !== undefined) {
        setEmotionOverride(partial.emotionOverride);
      }
      if (partial.isRecording !== undefined) {
        setIsRecording(partial.isRecording);
      }
      if (partial.isStreaming !== undefined) {
        setIsStreaming(partial.isStreaming);
      }

      if (isConnected) {
        sendControlRaw({
          mode: partial.mode,
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
