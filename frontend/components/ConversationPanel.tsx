import type { TranscriptMessage } from '@/types/janus';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

type ConversationPanelProps = {
  transcripts: TranscriptMessage[];
};

/**
 * Displays the most recent responses and rolling transcript history.
 */
export default function ConversationPanel({
  transcripts,
}: ConversationPanelProps) {
  const lastMessage = transcripts[0];
  const secondLastMessage = transcripts[1];

  const formatTime = (timestamp?: number): string => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <Card>
        <CardHeader>
          <CardTitle>Now Speaking</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {lastMessage && (
              <div>
                <div className="text-foreground bg-muted border-2 border-black p-3 font-mono text-sm shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  {lastMessage.text}
                </div>
              </div>
            )}
            {secondLastMessage && (
              <div>
                <div className="text-xs text-muted-foreground mb-1 uppercase font-bold">
                  Last Utterance
                </div>
                <div className="text-muted-foreground bg-white border-2 border-black p-3 font-mono text-sm shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  {secondLastMessage.text}
                </div>
              </div>
            )}
            {!lastMessage && (
              <div className="text-muted-foreground italic text-sm">
                No voice data received yet. Press PTT to speak or S to Stream.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader>
          <CardTitle>Transcript History</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <div className="space-y-3">
            {transcripts.length > 0 ? (
              transcripts.map((msg, index) => {
                const isAssistant = index % 2 === 0;
                const timeStr = msg.timestamp ? formatTime(msg.timestamp) : '—';
                const timeParts = timeStr.split(':');
                const displayTime =
                  timeParts.length === 3
                    ? `${timeParts[0]}:${timeParts[1]}:${timeParts[2]}`
                    : timeStr;

                return (
                  <div key={msg.id || index} className="space-y-1">
                    <div className="text-xs text-muted-foreground font-mono">
                      {displayTime}
                    </div>
                    <div
                      className={`p-2 border-2 border-black text-sm font-mono shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${isAssistant
                          ? 'text-foreground bg-muted'
                          : 'text-foreground bg-white'
                        }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8 text-xs text-muted-foreground">
                History is empty.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
