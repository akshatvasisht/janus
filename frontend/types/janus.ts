export type JanusMode = 'semantic' | 'text_only' | 'morse';

export type EmotionOverride = 'auto' | 'relaxed' | 'panicked';

// Control message sent TO backend (matches backend exactly)
export type ControlMessage = {
  type: 'control';
  is_streaming?: boolean | null;
  is_recording?: boolean | null;
  mode?: JanusMode | null;
  emotion_override?: EmotionOverride | null;
};

export type ControlStateUpdate = Partial<{
  isRecording: boolean;
  isStreaming: boolean;
  mode: JanusMode;
  emotionOverride: EmotionOverride;
}>;

export type HealthResponse = {
  status: 'ok';
};

// Transcript message FROM backend
export type TranscriptMessage = {
  type: 'transcript';
  text: string;
  start_ms?: number | null;
  end_ms?: number | null;
  avg_pitch_hz?: number | null;
  avg_energy?: number | null;
  // Frontend-only fields for UI
  id?: string; // Generate on frontend
  timestamp?: number; // Use created_at_ms or Date.now()
  mode?: JanusMode;
  emotionOverride?: EmotionOverride;
  inferredEmotion?: string;
};

export type IncomingTranscriptMessage = Omit<
  TranscriptMessage,
  'id' | 'timestamp'
>;

// Packet summary FROM backend
export type PacketSummaryMessage = {
  type: 'packet_summary'; // Note: underscore, not hyphen
  bytes: number;
  mode: JanusMode;
  created_at_ms: number;
};

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export type VoiceVerificationStatus = 'verified' | 'failed';

export type VoiceVerificationResponse = {
  status: VoiceVerificationStatus;
  transcript?: string;
};
