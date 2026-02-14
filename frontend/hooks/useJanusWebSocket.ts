'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ControlMessage,
  TranscriptMessage,
  PacketSummaryMessage,
  ConnectionStatus,
  IncomingTranscriptMessage,
  ControlStateMessage,
} from '@/types/janus';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000/ws/janus';

// Query keys for React Query
export const queryKeys = {
  transcripts: ['janus', 'transcripts'] as const,
  lastPacket: ['janus', 'lastPacket'] as const,
  connectionStatus: ['janus', 'connectionStatus'] as const,
  packetHistory: ['janus', 'packetHistory'] as const,
  controlState: ['janus', 'controlState'] as const,
};

type UseJanusWebSocketResult = {
  connectionStatus: ConnectionStatus;
  transcripts: TranscriptMessage[];
  lastPacket: PacketSummaryMessage | null;
  packetHistory: PacketSummaryMessage[];
  sendControl: (control: Partial<ControlMessage>) => void;
  isConnected: boolean;
  lastError: string | null;
  reconnect: () => void;
  disconnect: () => void;
};

const isJanusMode = (
  value: unknown
): value is PacketSummaryMessage['mode'] => {
  return (
    value === 'semantic' || value === 'text_only' || value === 'morse'
  );
};

const isTranscriptMessage = (
  data: unknown
): data is IncomingTranscriptMessage => {
  return (
    typeof data === 'object' &&
    data !== null &&
    (data as { type?: unknown }).type === 'transcript' &&
    typeof (data as { text?: unknown }).text === 'string'
  );
};

const isPacketSummaryMessage = (
  data: unknown
): data is PacketSummaryMessage => {
  return (
    typeof data === 'object' &&
    data !== null &&
    (data as { type?: unknown }).type === 'packet_summary' &&
    typeof (data as { bytes?: unknown }).bytes === 'number' &&
    typeof (data as { created_at_ms?: unknown }).created_at_ms === 'number' &&
    isJanusMode((data as { mode?: unknown }).mode)
  );
};

const isControlStateMessage = (
  data: unknown
): data is ControlStateMessage => {
  return (
    typeof data === 'object' &&
    data !== null &&
    (data as { type?: unknown }).type === 'control_state' &&
    typeof (data as { is_streaming?: unknown }).is_streaming === 'boolean' &&
    typeof (data as { is_recording?: unknown }).is_recording === 'boolean' &&
    isJanusMode((data as { mode?: unknown }).mode)
  );
};

/**
 * WebSocket hook for Janus backend communication.
 *
 * Manages WebSocket connection lifecycle, automatic reconnection, and React Query
 * cache updates for transcripts and packet summaries. Handles sending control messages
 * to the backend and receiving transcript/packet events.
 *
 * @returns Object containing connection status, transcripts, last packet summary,
 *   control message sender, and connection management functions.
 */
export function useJanusWebSocket(): UseJanusWebSocketResult {
  const wsRef = useRef<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('disconnected');
  const [lastError, setLastError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Load persisted data on mount
  useEffect(() => {
    const persistedTranscripts = localStorage.getItem('janus_transcripts');
    if (persistedTranscripts) {
      try {
        queryClient.setQueryData(queryKeys.transcripts, JSON.parse(persistedTranscripts));
      } catch (e) {
        console.error('Failed to parse persisted transcripts', e);
      }
    }

    const persistedPacketHistory = localStorage.getItem('janus_packetHistory');
    if (persistedPacketHistory) {
      try {
        queryClient.setQueryData(queryKeys.packetHistory, JSON.parse(persistedPacketHistory));
      } catch (e) {
        console.error('Failed to parse persisted packet history', e);
      }
    }
  }, [queryClient]);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { data: transcripts = [] } = useQuery<TranscriptMessage[]>({
    queryKey: queryKeys.transcripts,
    queryFn: async () => [],
    initialData: [],
    enabled: false, // Managed via WebSocket pushes
  });

  const { data: lastPacket } = useQuery<PacketSummaryMessage | null>({
    queryKey: queryKeys.lastPacket,
    queryFn: async () => null,
    initialData: null,
    enabled: false,
  });

  const { data: packetHistory = [] } = useQuery<PacketSummaryMessage[]>({
    queryKey: queryKeys.packetHistory,
    queryFn: async () => [],
    initialData: [],
    enabled: false,
  });

  const sendControlMutation = useMutation<void, Error, Partial<ControlMessage>>({
    mutationFn: async (control) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const message: ControlMessage = {
          type: 'control',
          ...control,
        };
        wsRef.current.send(JSON.stringify(message));
        return;
      }

      throw new Error('WebSocket not connected');
    },
  });

  const connect = useCallback(function connectSocket() {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnectionStatus('connected');
      setLastError(null);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as unknown;

        if (isTranscriptMessage(data)) {
          const timestamp = data.end_ms ?? data.start_ms ?? Date.now();
          const transcript: TranscriptMessage = {
            ...data,
            id:
              typeof crypto !== 'undefined' && 'randomUUID' in crypto
                ? crypto.randomUUID()
                : `transcript-${timestamp}`,
            timestamp,
          };

          queryClient.setQueryData<TranscriptMessage[]>(
            queryKeys.transcripts,
            (old = []) => {
              const next = [transcript, ...old];
              localStorage.setItem('janus_transcripts', JSON.stringify(next.slice(0, 100)));
              return next;
            }
          );
          return;
        }

        if (isPacketSummaryMessage(data)) {
          queryClient.setQueryData<PacketSummaryMessage>(
            queryKeys.lastPacket,
            data
          );

          queryClient.setQueryData<PacketSummaryMessage[]>(
            queryKeys.packetHistory,
            (old = []) => {
              const next = [...old, data];
              const sliced = next.slice(-200);
              localStorage.setItem('janus_packetHistory', JSON.stringify(sliced));
              return sliced;
            }
          );
          return;
        }

        if (isControlStateMessage(data)) {
          queryClient.setQueryData<ControlStateMessage>(
            queryKeys.controlState,
            data
          );
          return;
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      setConnectionStatus('disconnected');
      setLastError('WebSocket connection failed. Check server status.');
      console.error('WebSocket error event reported:', event);
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;

      reconnectTimeoutRef.current = setTimeout(() => {
        connectSocket();
      }, 3000);
    };

    wsRef.current = ws;
  }, [queryClient]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  useEffect(() => {
    queryClient.setQueryData<ConnectionStatus>(
      queryKeys.connectionStatus,
      connectionStatus
    );
  }, [connectionStatus, queryClient]);

  return {
    connectionStatus,
    transcripts,
    lastPacket,
    packetHistory,
    sendControl: sendControlMutation.mutate,
    isConnected: connectionStatus === 'connected',
    lastError,
    reconnect: connect,
    disconnect,
  };
}
