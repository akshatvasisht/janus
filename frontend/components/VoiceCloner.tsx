'use client';

import React, { useState, useRef, useEffect } from 'react';

const API_URL = 'http://localhost:8000';
const VERIFICATION_PHRASE = 'The quick brown fox jumps over the lazy dog.';

type VoiceClonerProps = {
  disabled?: boolean;
};

/**
 * Voice cloning component for reference audio upload and verification.
 * 
 * Provides a modal interface for recording and uploading reference audio
 * for voice cloning. Verifies the recording matches the verification phrase
 * before accepting it as a voice reference.
 * 
 * @param props - Component props.
 * @param props.disabled - Whether the component is disabled (e.g., disconnected).
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = async () => {
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
        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        // Upload audio
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

      const data = await response.json();

      if (data.status === 'verified') {
        setStatus('success');
        setErrorMessage('');
        setTranscript('');
        // Close modal after 2 seconds
        setTimeout(() => {
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
          w-full px-4 py-2 rounded-lg border transition-colors text-sm font-medium
          ${
            disabled
              ? 'bg-slate-800 opacity-50 cursor-not-allowed border-slate-700 text-slate-500'
              : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-750 hover:text-white'
          }
        `}
      >
        Clone Voice
      </button>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 max-w-md w-full">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-bold text-slate-100">Voice Cloning</h2>
              <button
                onClick={closeModal}
                className="text-slate-400 hover:text-slate-200 transition-colors"
                disabled={isVerifying}
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
                  Verification Phrase
                </p>
                <p className="text-slate-200 text-lg font-medium bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  {VERIFICATION_PHRASE}
                </p>
              </div>

              <div className="flex flex-col items-center gap-3">
                {!isRecording && !isVerifying && status !== 'success' && (
                  <button
                    onClick={startRecording}
                    className="w-full px-4 py-3 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
                  >
                    Start Recording
                  </button>
                )}

                {isRecording && (
                  <>
                    <div className="flex items-center gap-2 text-red-400">
                      <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                      <span className="text-sm font-medium">Recording...</span>
                    </div>
                    <button
                      onClick={stopRecording}
                      className="w-full px-4 py-3 rounded-lg bg-slate-700 hover:bg-slate-600 text-white font-medium transition-colors"
                    >
                      Stop Recording
                    </button>
                  </>
                )}

                {isVerifying && (
                  <div className="flex flex-col items-center gap-2 py-4">
                    <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-slate-400">Verifying...</span>
                  </div>
                )}

                {status === 'success' && (
                  <div className="w-full px-4 py-3 rounded-lg bg-green-900/30 border border-green-700 text-green-200 text-center">
                    ✓ Success! Voice Cloned
                  </div>
                )}

                {status === 'error' && (
                  <div className="w-full px-4 py-3 rounded-lg bg-red-900/30 border border-red-700 text-red-200">
                    <p className="font-medium mb-1">Failed: {errorMessage}</p>
                    {transcript && (
                      <p className="text-xs text-red-300 mt-1">
                        You said: &quot;{transcript}&quot;
                      </p>
                    )}
                    <p className="text-xs text-red-300 mt-2">
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

