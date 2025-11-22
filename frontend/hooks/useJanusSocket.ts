import { useState, useCallback, useEffect } from 'react';
import {
  JanusMode,
  EmotionOverride,
  ControlMessage,
  TranscriptMessage,
  PacketSummaryMessage,
  ConnectionStatus,
} from '../types/janus';

export type JanusSocketState = {
  status: ConnectionStatus;
  mode: JanusMode;
  emotionOverride: EmotionOverride;
  isRecording: boolean;
  isStreaming: boolean;
  transcripts: TranscriptMessage[];
  lastPacketSummary?: PacketSummaryMessage;
  lastError?: string | null;
  sendControl: (control: Partial<ControlMessage>) => void;
};

// TODO: Replace this entire hook with real WebSocket/Socket.io integration
// This is currently a complete mock implementation for UI development and testing
export function useJanusSocket(): JanusSocketState {
  // TODO: Replace with real connection status from backend
  const [status, setStatus] = useState<ConnectionStatus>('connected'); // Default to connected for demo
  const [mode, setMode] = useState<JanusMode>(0);
  const [emotionOverride, setEmotionOverride] =
    useState<EmotionOverride>('auto');
  const [isRecording, setIsRecording] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [lastPacketSummary, setLastPacketSummary] = useState<
    PacketSummaryMessage | undefined
  >();
  const [lastError, setLastError] = useState<string | null>(null);

  // TODO: Remove - this is mock data generation for UI development
  const generateMockTranscript = (
    currentMode: JanusMode,
    override: EmotionOverride
  ) => {
    const phrases = [
      'Target acquired at coordinates 45.2, 12.9.',
      'Status report: All systems nominal.',
      'Requesting backup immediately!',
      'The quick brown fox jumps over the lazy dog.',
      'Interference detected on sector 7.',
      'Initiating sequence alpha-nine.',
      'Confirm receipt of package.',
      'Holding position until further notice.',
    ];

    const text = phrases[Math.floor(Math.random() * phrases.length)];

    return {
      type: 'transcript' as const,
      id: Math.random().toString(36).substring(7),
      text,
      mode: currentMode,
      inferredEmotion:
        override === 'auto'
          ? Math.random() > 0.5
            ? 'Calm'
            : 'Neutral'
          : undefined,
      emotionOverride: override,
      timestamp: Date.now(),
    };
  };

  // TODO: Remove - this is mock packet generation for UI development
  const generateMockPacket = (currentMode: JanusMode) => {
    const rawBytes = Math.floor(Math.random() * 5000) + 3000;
    const compression = currentMode === 1 ? 200 : 60; // Higher compression for text mode

    return {
      type: 'packet-summary' as const,
      mode: currentMode,
      bytes: Math.floor(rawBytes / compression),
      estimatedRawBytes: rawBytes,
      timestamp: Date.now(),
    };
  };

  // TODO: Replace with real WebSocket/Socket.io message sending to backend
  const sendControl = useCallback(
    (partial: Partial<ControlMessage>) => {
      // Update local state
      if (partial.mode !== undefined) setMode(partial.mode);
      if (partial.emotionOverride !== undefined)
        setEmotionOverride(partial.emotionOverride);
      if (partial.isRecording !== undefined)
        setIsRecording(partial.isRecording);
      if (partial.isStreaming !== undefined)
        setIsStreaming(partial.isStreaming);

      // TODO: Remove - Mock response logic for UI testing
      // Real implementation should send control messages to backend and receive actual transcript/packet data

      const newRecordingState = partial.isRecording;

      // If we stopped recording, generate a transcript + packet
      if (newRecordingState === false) {
        setTimeout(() => {
          const newTranscript = generateMockTranscript(
            partial.mode ?? mode,
            partial.emotionOverride ?? emotionOverride
          );
          const newPacket = generateMockPacket(partial.mode ?? mode);

          setTranscripts((prev) => [newTranscript, ...prev]);
          setLastPacketSummary(newPacket);
        }, 500);
      }
    },
    [mode, emotionOverride]
  );

  // TODO: Remove - Mock streaming simulation for UI testing
  // Real implementation should receive streaming transcripts from backend
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (isStreaming) {
      interval = setInterval(() => {
        if (Math.random() > 0.7) {
          // Randomly receive things
          const newTranscript = generateMockTranscript(mode, emotionOverride);
          const newPacket = generateMockPacket(mode);

          setTranscripts((prev) => [newTranscript, ...prev]);
          setLastPacketSummary(newPacket);
        }
      }, 2000);
    }

    return () => clearInterval(interval);
  }, [isStreaming, mode, emotionOverride]);

  return {
    status,
    mode,
    emotionOverride,
    isRecording,
    isStreaming,
    transcripts,
    lastPacketSummary,
    lastError,
    sendControl,
  };
}
