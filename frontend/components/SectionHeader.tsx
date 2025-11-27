'use client';

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type SectionHeaderProps = {
  title: string;
  description?: string;
  className?: string;
  rightSlot?: ReactNode;
};

/**
 * Standardized section header with optional description and right-aligned slot.
 */
export function SectionHeader({
  title,
  description,
  className,
  rightSlot,
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-b-2 border-black pb-3',
        className
      )}
    >
      <div className="space-y-1">
        <h1 className="text-3xl font-black uppercase tracking-tight">{title}</h1>
        {description ? (
          <p className="text-muted-foreground text-sm">{description}</p>
        ) : null}
      </div>
      {rightSlot ? <div className="shrink-0">{rightSlot}</div> : null}
    </div>
  );
}
