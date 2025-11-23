import React from 'react';
import { EmotionOverride } from '../types/janus';

type EmotionSelectorProps = {
  value: EmotionOverride;
  onChange: (v: EmotionOverride) => void;
};

export default function EmotionSelector({ value, onChange }: EmotionSelectorProps) {
  const options: EmotionOverride[] = ['auto', 'relaxed', 'panicked'];

  return (
    <div className="flex gap-2">
      {options.map((opt) => {
        const isActive = value === opt;
        let activeClass = '';
        
        // Distinct colors for emotions
        if (isActive) {
            if (opt === 'panicked') activeClass = 'bg-red-900/50 border-red-500 text-red-100';
            else if (opt === 'relaxed') activeClass = 'bg-cyan-900/50 border-cyan-500 text-cyan-100';
            else activeClass = 'bg-blue-900/50 border-blue-500 text-blue-100'; // auto
        } else {
            activeClass = 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600';
        }

        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className={`
              flex-1 px-3 py-2 rounded-md border text-xs font-medium capitalize transition-all
              ${activeClass}
            `}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

