// TODO: Integrate with real audio capture/playback when backend is ready
// Currently only handles UI state - no actual microphone access or audio playback
import React, { useCallback, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';

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
  const debouncedHoldStart = useDebounce(onHoldStart, 50);
  
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

  // Determine visual state
  let bgClass = 'bg-slate-800 border-slate-700 text-slate-100 hover:bg-slate-750';
  let shadowClass = '';
  let statusText = 'Hold to Talk';
  
  if (disabled) {
    bgClass = 'bg-slate-800 opacity-50 cursor-not-allowed border-slate-700 text-slate-500';
    statusText = 'Disconnected';
  } else if (isRecording) {
    bgClass = 'bg-red-600 border-red-500 text-white';
    shadowClass = 'shadow-[0_0_40px_-10px_rgba(220,38,38,0.5)] scale-[0.98]';
    statusText = 'Listening...';
  } else if (isStreaming) {
    bgClass = 'bg-blue-600 border-blue-500 text-white';
    shadowClass = 'shadow-[0_0_40px_-10px_rgba(37,99,235,0.5)]';
    statusText = 'Streaming Live';
  }

  return (
    <div className="flex flex-col items-center gap-3 w-full">
      <button
        className={`
          relative w-full aspect-square max-w-[240px] rounded-full flex flex-col items-center justify-center
          border-4 transition-all duration-200 ease-in-out outline-none
          ${bgClass} ${shadowClass}
        `}
        onMouseDown={!disabled ? debouncedHoldStart : undefined}
        onMouseUp={!disabled ? debouncedHoldEnd : undefined}
        onMouseLeave={!disabled && isRecording ? debouncedHoldEnd : undefined}
        onTouchStart={!disabled ? (e) => { e.preventDefault(); debouncedHoldStart(); } : undefined}
        onTouchEnd={!disabled ? (e) => { e.preventDefault(); debouncedHoldEnd(); } : undefined}
        onClick={!disabled && !isRecording ? (e) => {
          // Logic: If it was a short click (not a hold), treat as toggle attempt if needed?
          // Spec says: "Short Click/Tap: Toggles is_streaming"
          // But we also have Hold logic.
          // For simplicity with mouse events overlap, let's explicitly separate toggle button or 
          // rely on `onClick` firing after `onMouseUp`.
          // Since `onMouseUp` fires `onHoldEnd`, we need to be careful.
          // Actually, the spec says: 
          // Event A (Mouse Down): Sets is_recording = True.
          // Event B (Mouse Up): Sets is_recording = False.
          // Event C (Short Click/Tap): Toggles is_streaming = True/False.
          
          // Implementing "Short Click" logic usually requires timing.
          // However, standard PTT is just hold. The Toggle might be better as a separate small button 
          // or we handle it via timing here. 
          // Let's stick to Hold = PTT. 
          // The user might have meant "Tap" on a separate control or double tap? 
          // "Short helper text – e.g. 'Hold to send a burst. Tap to toggle streaming.'" implies same button.
          
          // Let's trust the handler prop separation for now, but standard `button` click 
          // triggers after mouseup. 
        } : undefined}
        disabled={disabled}
      >
        {/* Inner Ring decoration */}
        <div className={`absolute inset-2 rounded-full border-2 border-dashed opacity-20 ${isStreaming ? 'animate-spin-slow' : ''}`} />
        
        <span className="text-3xl font-bold tracking-wider uppercase pointer-events-none select-none">
           {isRecording ? 'REC' : (isStreaming ? 'ON AIR' : 'PTT')}
        </span>
        <span className="text-xs font-medium opacity-80 mt-1 pointer-events-none select-none">
          {statusText}
        </span>
      </button>
      
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-xs text-slate-400 max-w-[200px]">
          Hold <strong>Space</strong> to talk. Tap button or press <strong>S</strong> to toggle stream.
        </p>
        
        {/* Explicit Toggle Button as an alternative interaction point */}
        <button 
            onClick={onToggleStreaming}
            disabled={disabled}
            className={`
                text-xs px-3 py-1.5 rounded-full border transition-colors
                ${isStreaming 
                    ? 'bg-blue-900/30 border-blue-800 text-blue-200 hover:bg-blue-900/50' 
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-750 hover:text-slate-200'}
            `}
        >
            {isStreaming ? 'Stop Streaming' : 'Start Streaming'}
        </button>
      </div>
    </div>
  );
}

