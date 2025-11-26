'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  ControlMessage,
  TranscriptMessage,
  PacketSummaryMessage,
  ConnectionStatus,
} from '../types/janus';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000/ws/janus';

// Query keys for React Query
export const queryKeys = {
  transcripts: ['janus', 'transcripts'] as const,
  lastPacket: ['janus', 'lastPacket'] as const,
  connectionStatus: ['janus', 'connectionStatus'] as const,
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
export function useJanusWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('disconnected');
  const queryClient = useQueryClient();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>(null);

  // Query for transcripts (managed via WebSocket updates)
  const { data: transcripts = [] } = useQuery<TranscriptMessage[]>({
    queryKey: queryKeys.transcripts,
    queryFn: async () => {
      // Data is managed via WebSocket updates, this is just a placeholder
      // Return initial data - actual updates come from setQueryData in ws.onmessage
      return [];
    },
    initialData: [],
    enabled: false, // Don't auto-fetch, we manage via WebSocket
  });

  // Query for last packet summary
  const { data: lastPacket } = useQuery<PacketSummaryMessage | null>({
    queryKey: queryKeys.lastPacket,
    queryFn: async () => {
      // Data is managed via WebSocket updates, this is just a placeholder
      // Return initial data - actual updates come from setQueryData in ws.onmessage
      return null;
    },
    initialData: null,
    enabled: false, // Don't auto-fetch, we manage via WebSocket
  });

  // Mutation for sending control messages
  const sendControlMutation = useMutation({
    mutationFn: async (control: Partial<ControlMessage>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const message: ControlMessage = {
          type: 'control',
          ...control,
        };
        wsRef.current.send(JSON.stringify(message));
      } else {
        throw new Error('WebSocket not connected');
      }
    },
  });

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    setConnectionStatus('connecting');
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnectionStatus('connected');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'transcript') {
          // Add frontend-only fields
          const transcript: TranscriptMessage = {
            ...data,
            id: `transcript-${Date.now()}-${Math.random()}`,
            timestamp: data.created_at_ms || Date.now(),
          };

          // Update transcripts query cache (prepend new transcript)
          queryClient.setQueryData<TranscriptMessage[]>(
            queryKeys.transcripts,
            (old = []) => [transcript, ...old]
          );
        } else if (data.type === 'packet_summary') {
          // Update last packet query cache
          queryClient.setQueryData<PacketSummaryMessage>(
            queryKeys.lastPacket,
            data
          );
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('disconnected');
      wsRef.current = null;

      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    wsRef.current = ws;
  }, [queryClient]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount/unmount

  // Update connection status in query cache
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
    sendControl: sendControlMutation.mutate,
    isConnected: connectionStatus === 'connected',
    reconnect: connect,
    disconnect,
  };
}
