import React from 'react';
import { JanusMode } from '../types/janus';
import { Button } from './ui/button';

type ModeToggleProps = {
  mode: JanusMode;
  onChange: (mode: JanusMode) => void;
  isMorseEnabled?: boolean;
};

export default function ModeToggle({
  mode,
  onChange,
  isMorseEnabled = true,
}: ModeToggleProps) {
  const options: { value: JanusMode; label: string; disabled?: boolean }[] = [
    { value: 'semantic', label: 'Semantic Voice' },
    { value: 'text_only', label: 'Text Only' },
    { value: 'morse', label: 'Morse Code', disabled: !isMorseEnabled },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {options.map((opt) => {
        const isActive = mode === opt.value;
        return (
          <Button
            key={opt.value}
            variant={isActive ? 'default' : 'outline'}
            className={isActive ? 'font-bold' : ''}
            disabled={opt.disabled}
            onClick={() => onChange(opt.value)}
            title={opt.disabled ? 'Unavailable' : ''}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
}
