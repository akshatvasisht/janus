import React from 'react';
import { JanusMode } from '../types/janus';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Label } from './ui/label';

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
  return (
    <RadioGroup
      value={mode}
      onValueChange={(value) => onChange(value as JanusMode)}
    >
      <div className="flex items-center space-x-2 mb-3">
        <RadioGroupItem value="semantic" id="semantic" />
        <Label
          htmlFor="semantic"
          className="text-foreground cursor-pointer font-bold"
        >
          Semantic Voice
        </Label>
      </div>
      <div className="flex items-center space-x-2 mb-3">
        <RadioGroupItem value="text_only" id="text_only" />
        <Label
          htmlFor="text_only"
          className="text-foreground cursor-pointer font-bold"
        >
          Text Only
        </Label>
      </div>
      <div className="flex items-center space-x-2">
        <RadioGroupItem
          value="morse"
          id="morse"
          disabled={!isMorseEnabled}
        />
        <Label
          htmlFor="morse"
          className={`text-foreground font-bold ${
            !isMorseEnabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
          }`}
          title={!isMorseEnabled ? 'Stretch goal (not implemented)' : ''}
        >
          Morse Code
        </Label>
      </div>
    </RadioGroup>
  );
}
