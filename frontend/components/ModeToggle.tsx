import React from 'react';
import { JanusMode } from '../types/janus';

type ModeToggleProps = {
  mode: JanusMode;
  onChange: (mode: JanusMode) => void;
  isMorseEnabled?: boolean;
};

/**
 * Mode selection toggle component for Janus transmission modes.
 * 
 * Provides buttons to switch between semantic voice, text-only, and Morse code modes.
 * Supports disabling specific modes (e.g., Morse code) when not available.
 * 
 * @param props - Component props.
 * @param props.mode - Currently selected transmission mode.
 * @param props.onChange - Callback invoked when mode selection changes.
 * @param props.isMorseEnabled - Whether Morse code mode is available. Defaults to true.
 */
export default function ModeToggle({ mode, onChange, isMorseEnabled = true }: ModeToggleProps) {
  const options: { value: JanusMode; label: string; disabled?: boolean }[] = [
    { value: 'semantic', label: 'Semantic' },
    { value: 'text_only', label: 'Text Only' },
    { value: 'morse', label: 'Morse', disabled: !isMorseEnabled },
  ];

  return (
    <div className="flex w-full bg-slate-900 p-1 rounded-lg border border-slate-800">
      {options.map((opt) => {
        const isActive = mode === opt.value;
        return (
          <button
            key={opt.value}
            onClick={() => !opt.disabled && onChange(opt.value)}
            disabled={opt.disabled}
            className={`
              flex-1 py-1.5 text-xs font-medium rounded-md transition-all duration-200
              ${isActive 
                ? 'bg-blue-600 text-white shadow-sm' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}
              ${opt.disabled ? 'opacity-40 cursor-not-allowed hover:bg-transparent' : ''}
            `}
            title={opt.disabled ? "Mode not available" : ""}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

