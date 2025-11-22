export type JanusMode = 0 | 1 | 2; // 0=Semantic, 1=Text, 2=Morse

export type EmotionOverride = "auto" | "calm" | "urgent";

// TODO: Verify these message types match the actual backend protocol when integrating

export type ControlMessage = {
  type: "control";
  mode: JanusMode;
  isRecording: boolean;
  isStreaming: boolean;
  emotionOverride: EmotionOverride;
};

export type TranscriptMessage = {
  type: "transcript";
  id: string;
  text: string;
  mode: JanusMode;
  inferredEmotion?: string;
  emotionOverride?: EmotionOverride;
  timestamp: number; // ms since epoch
};

export type PacketSummaryMessage = {
  type: "packet-summary";
  mode: JanusMode;
  bytes: number;
  estimatedRawBytes?: number;
  timestamp: number;
};

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

