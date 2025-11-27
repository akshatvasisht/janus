'use client';

import { useEffect, useRef, useState } from 'react';
import type { VoiceVerificationResponse } from '@/types/janus';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const VERIFICATION_PHRASE = 'The quick brown fox jumps over the lazy dog.';

type VoiceClonerProps = {
  disabled?: boolean;
};

/**
 * Voice cloning component for reference audio upload and verification.
 *
 * Provides a modal interface for recording and uploading reference audio for
 * voice cloning. Verifies the recording against a known phrase before
 * accepting it as a voice reference.
 */
export default function VoiceCloner({ disabled = false }: VoiceClonerProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [transcript, setTranscript] = useState<string>('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const successTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
      }
    };
  }, []);

  const resetSuccessTimer = () => {
    if (successTimeoutRef.current) {
      clearTimeout(successTimeoutRef.current);
      successTimeoutRef.current = null;
    }
  };

  const startRecording = async () => {
    resetSuccessTimer();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        await uploadAudio();
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setStatus('idle');
      setErrorMessage('');
    } catch (error) {
      console.error('Error starting recording:', error);
      setStatus('error');
      setErrorMessage('Failed to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAudio = async () => {
    setIsVerifying(true);
    setStatus('idle');
    resetSuccessTimer();

    try {
      const audioBlob = new Blob(audioChunksRef.current, {
        type: 'audio/webm;codecs=opus',
      });

      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'recording.webm');

      const response = await fetch(`${API_URL}/api/voice/verify`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Voice verification request failed');
      }

      const data = (await response.json()) as VoiceVerificationResponse;

      if (data.status === 'verified') {
        setStatus('success');
        setErrorMessage('');
        setTranscript('');
        resetSuccessTimer();
        successTimeoutRef.current = setTimeout(() => {
          setIsModalOpen(false);
          setStatus('idle');
        }, 2000);
      } else {
        setStatus('error');
        setErrorMessage(data.transcript || 'Verification failed');
        setTranscript(data.transcript || '');
      }
    } catch (error) {
      console.error('Error uploading audio:', error);
      setStatus('error');
      setErrorMessage('Failed to upload audio. Please try again.');
      setTranscript('');
    } finally {
      setIsVerifying(false);
    }
  };

  const openModal = () => {
    setIsModalOpen(true);
    setStatus('idle');
    setErrorMessage('');
    setTranscript('');
  };

  const closeModal = () => {
    if (isRecording) {
      stopRecording();
    }
    setIsModalOpen(false);
    setStatus('idle');
    setErrorMessage('');
    setTranscript('');
  };

  return (
    <>
      <button
        onClick={openModal}
        disabled={disabled}
        className={`
          w-full px-4 py-2 border-2 border-black text-sm font-bold uppercase tracking-wide
          transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]
          ${disabled
            ? 'bg-muted text-muted-foreground cursor-not-allowed opacity-60'
            : 'bg-primary text-primary-foreground hover:bg-primary/80 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]'
          }
        `}
      >
        Clone Voice
      </button>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-white text-foreground border-3 border-black p-6 max-w-md w-full shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-black uppercase">Voice Cloning</h2>
              <button
                onClick={closeModal}
                className="text-muted-foreground hover:text-foreground transition-colors font-bold"
                disabled={isVerifying}
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mb-2">
                  Verification Phrase
                </p>
                <p className="text-foreground text-lg font-medium bg-muted border-2 border-black p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  {VERIFICATION_PHRASE}
                </p>
              </div>

              <div className="flex flex-col items-center gap-3">
                {!isRecording && !isVerifying && status !== 'success' && (
                  <button
                    onClick={startRecording}
                    className="w-full px-4 py-3 border-2 border-black bg-destructive text-destructive-foreground font-bold uppercase tracking-wide shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-destructive/80 transition-all"
                  >
                    Start Recording
                  </button>
                )}

                {isRecording && (
                  <>
                    <div className="flex items-center gap-2 text-destructive">
                      <div className="w-3 h-3 bg-destructive rounded-full animate-pulse" />
                      <span className="text-sm font-medium uppercase">Recording...</span>
                    </div>
                    <button
                      onClick={stopRecording}
                      className="w-full px-4 py-3 border-2 border-black bg-muted text-foreground font-bold uppercase tracking-wide shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-white transition-all"
                    >
                      Stop Recording
                    </button>
                  </>
                )}

                {isVerifying && (
                  <div className="flex flex-col items-center gap-2 py-4">
                    <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-muted-foreground uppercase">Verifying...</span>
                  </div>
                )}

                {status === 'success' && (
                  <div className="w-full px-4 py-3 border-2 border-black bg-secondary text-secondary-foreground font-bold uppercase text-center shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    ✓ Success! Voice Cloned
                  </div>
                )}

                {status === 'error' && (
                  <div className="w-full px-4 py-3 border-2 border-black bg-red-500 text-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    <p className="font-bold mb-1 uppercase">Failed: {errorMessage}</p>
                    {transcript && (
                      <p className="text-xs mt-1">
                        You said: &quot;{transcript}&quot;
                      </p>
                    )}
                    <p className="text-xs mt-2">
                      Please try again.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
