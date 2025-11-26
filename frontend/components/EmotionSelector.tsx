import React from 'react';
import { EmotionOverride } from '../types/janus';
import { Button } from './ui/button';

type EmotionSelectorProps = {
  value: EmotionOverride;
  onChange: (v: EmotionOverride) => void;
};

export default function EmotionSelector({
  value,
  onChange,
}: EmotionSelectorProps) {
  const options: { value: EmotionOverride; label: string }[] = [
    { value: 'auto', label: 'Auto' },
    { value: 'relaxed', label: 'Relaxed' },
    { value: 'panicked', label: 'Panicked' },
  ];

  return (
    <div className="grid grid-cols-3 gap-2">
      {options.map((opt) => {
        const isActive = value === opt.value;
        return (
          <Button
            key={opt.value}
            variant={isActive ? 'default' : 'outline'}
            onClick={() => onChange(opt.value)}
            className={isActive ? 'font-bold' : ''}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
}
