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
  const modeValue =
    mode === 'text_only' ? 'ptt' : mode === 'morse' ? 'continuous' : 'auto';

  return (
    <RadioGroup
      value={modeValue}
      onValueChange={(value) => {
        if (value === 'ptt') {
          onChange('text_only');
        } else if (value === 'continuous') {
          onChange('morse');
        } else {
          onChange('semantic');
        }
      }}
    >
      <div className="flex items-center space-x-2 mb-3">
        <RadioGroupItem value="auto" id="auto" />
        <Label
          htmlFor="auto"
          className="text-foreground cursor-pointer font-bold"
        >
          Automatic (VAD)
        </Label>
      </div>
      <div className="flex items-center space-x-2 mb-3">
        <RadioGroupItem value="ptt" id="ptt" />
        <Label
          htmlFor="ptt"
          className="text-foreground cursor-pointer font-bold"
        >
          Push-to-Talk
        </Label>
      </div>
      <div className="flex items-center space-x-2">
        <RadioGroupItem
          value="continuous"
          id="continuous"
          disabled={!isMorseEnabled}
        />
        <Label
          htmlFor="continuous"
          className={`text-foreground font-bold ${
            !isMorseEnabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
          }`}
          title={!isMorseEnabled ? 'Stretch goal (not implemented)' : ''}
        >
          Continuous Listen
        </Label>
      </div>
    </RadioGroup>
  );
}
