import React from 'react';
import { JanusMode } from '../types/janus';

type ModeToggleProps = {
  mode: JanusMode;
  onChange: (mode: JanusMode) => void;
  isMorseEnabled?: boolean;
};

export default function ModeToggle({ mode, onChange, isMorseEnabled = true }: ModeToggleProps) {
  const options: { value: JanusMode; label: string; disabled?: boolean }[] = [
    { value: 0, label: 'Semantic' },
    { value: 1, label: 'Text Only' },
    { value: 2, label: 'Morse', disabled: !isMorseEnabled },
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
            title={opt.disabled ? "Stretch goal (not implemented)" : ""}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

