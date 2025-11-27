import type { JanusMode } from '@/types/janus';
import { Button } from './ui/button';

type ModeToggleProps = {
  mode: JanusMode;
  onChange: (mode: JanusMode) => void;
  isMorseEnabled?: boolean;
};

/**
 * Three-way toggle for selecting Janus transport mode.
 */
export default function ModeToggle({
  mode,
  onChange,
  isMorseEnabled = true,
}: ModeToggleProps) {
  const options: { value: JanusMode; label: string; disabled?: boolean }[] = [
    { value: 'semantic', label: 'Semantic' },
    { value: 'text_only', label: 'Text' },
    { value: 'morse', label: 'Morse', disabled: !isMorseEnabled },
  ];

  return (
    <div className="grid grid-cols-3 overflow-hidden border-3 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
      {options.map((opt) => {
        const isActive = mode === opt.value;
        return (
          <Button
            key={opt.value}
            variant="ghost"
            className={`rounded-none h-10 border-x border-black/20 first:border-l-0 last:border-r-0 ${
              isActive
                ? 'bg-primary text-white font-bold'
                : 'bg-muted text-foreground font-medium hover:bg-primary/70 hover:text-white'
            } transition-colors`}
            disabled={opt.disabled}
            onClick={() => onChange(opt.value)}
            title={opt.disabled ? 'Unavailable' : ''}
            aria-pressed={isActive}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
}
