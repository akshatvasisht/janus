import type { JanusMode, PacketSummaryMessage } from '@/types/janus';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

type QuickStatsProps = {
  summary?: PacketSummaryMessage;
};

const MODE_LABELS: Record<JanusMode, string> = {
  semantic: 'Semantic',
  text_only: 'Text',
  morse: 'Morse',
};

/**
 * Compact status card summarizing the most recent packet.
 */
export default function QuickStats({ summary }: QuickStatsProps) {
  if (!summary) {
    return (
      <Card>
        <CardContent className="pt-6 text-center">
          <span className="text-xs text-muted-foreground italic">
            No packet data available yet.
          </span>
        </CardContent>
      </Card>
    );
  }

  const timestamp = summary.created_at_ms
    ? new Date(summary.created_at_ms).toLocaleTimeString()
    : '—';

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Packet Status</CardTitle>
          <span className="text-[10px] font-mono text-muted-foreground">
            {timestamp}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground text-sm">Packet Size</span>
            <span className="text-foreground text-sm font-mono">
              {summary.bytes} B
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground text-sm">Mode</span>
            <span className="text-foreground text-sm">
              {MODE_LABELS[summary.mode]}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
