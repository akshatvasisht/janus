// TODO: Integrate with real audio capture/playback when backend is ready
// Currently only handles UI state - no actual microphone access or audio playback
import React, { useEffect } from 'react';
import { Mic } from 'lucide-react';
import { useDebounce } from '../hooks/useDebounce';
import { Button } from './ui/button';

type PushToTalkProps = {
  isRecording: boolean;
  isStreaming: boolean;
  disabled?: boolean;
  onHoldStart: () => void;
  onHoldEnd: () => void;
  onToggleStreaming: () => void;
};

export default function PushToTalk({
  isRecording,
  isStreaming,
  disabled = false,
  onHoldStart,
  onHoldEnd,
  onToggleStreaming,
}: PushToTalkProps) {
  // Debounce hold start to prevent accidental triggers (50ms delay)
  const debouncedHoldStart = useDebounce(onHoldStart, 100);

  // Debounce hold end to prevent rapid state changes (100ms delay)
  const debouncedHoldEnd = useDebounce(onHoldEnd, 100);

  // Handle keyboard shortcuts
  useEffect(() => {
    if (disabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) return;

      if (e.code === 'Space') {
        e.preventDefault(); // Prevent scrolling
        debouncedHoldStart();
      } else if (e.code === 'KeyS') {
        onToggleStreaming();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        debouncedHoldEnd();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [disabled, debouncedHoldStart, debouncedHoldEnd, onToggleStreaming]);

  return (
    <div className="flex flex-col items-center w-full">
      <Button
        size="lg"
        className={`w-48 h-48 transition-all border-4 border-black rounded-none ${
          isRecording
            ? "bg-red-500 hover:bg-red-600 text-white shadow-none translate-x-[4px] translate-y-[4px]"
            : "bg-white hover:bg-gray-100 text-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px]"
        }`}
        disabled={disabled}
        onMouseDown={!disabled ? debouncedHoldStart : undefined}
        onMouseUp={!disabled ? debouncedHoldEnd : undefined}
        onMouseLeave={!disabled && isRecording ? debouncedHoldEnd : undefined}
        onTouchStart={
          !disabled
            ? (e) => {
                e.preventDefault();
                debouncedHoldStart();
              }
            : undefined
        }
        onTouchEnd={
          !disabled
            ? (e) => {
                e.preventDefault();
                debouncedHoldEnd();
              }
            : undefined
        }
      >
        <div className="flex flex-col items-center gap-2">
          <Mic
            className={`w-16 h-16 ${
              isRecording ? "text-white" : "text-black"
            }`}
          />
          <span
            className={`text-xs font-bold tracking-widest ${
              isRecording ? "text-white" : "text-black"
            }`}
          >
            {isRecording ? "TRANSMITTING" : "PUSH TO TALK"}
          </span>
        </div>
      </Button>
    </div>
  );
}
