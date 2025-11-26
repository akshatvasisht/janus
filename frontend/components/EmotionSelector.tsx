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
    <div className="grid grid-cols-3 overflow-hidden border-3 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
      {options.map((opt) => {
        const isActive = value === opt.value;
        return (
          <Button
            key={opt.value}
            variant="ghost"
            className={`rounded-none h-10 border-x border-black/20 first:border-l-0 last:border-r-0 ${
              isActive
                ? 'bg-primary text-white font-bold'
                : 'bg-muted text-foreground font-medium hover:bg-white'
            }`}
            onClick={() => onChange(opt.value)}
            aria-pressed={isActive}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
}
