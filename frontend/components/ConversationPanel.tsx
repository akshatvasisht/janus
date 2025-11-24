import { TranscriptMessage } from '../types/janus';

type ConversationPanelProps = {
  transcripts: TranscriptMessage[];
};

/**
 * Conversation panel component displaying transcript history and latest utterance.
 * 
 * Shows the most recent transcript message prominently with metadata badges,
 * and provides a scrollable history list of all received transcripts.
 * 
 * @param props - Component props.
 * @param props.transcripts - Array of transcript messages to display, ordered most recent first.
 */
export default function ConversationPanel({ transcripts }: ConversationPanelProps) {
  const lastMessage = transcripts[0];

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Latest Message Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
           <svg className="w-24 h-24 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
               <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
           </svg>
        </div>
        
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
            Now Speaking / Last Utterance
        </h2>
        
        {lastMessage ? (
          <div className="space-y-4 relative z-10">
            <p className="text-lg md:text-2xl font-light text-slate-50 leading-relaxed">
              "{lastMessage.text}"
            </p>
            
            <div className="flex flex-wrap gap-2">
              <Badge label={new Date(lastMessage.timestamp || Date.now()).toLocaleTimeString()} color="slate" />
              {lastMessage.avg_pitch_hz && (
                <Badge label={`Pitch: ${lastMessage.avg_pitch_hz.toFixed(0)}Hz`} color="blue" />
              )}
              {lastMessage.avg_energy && (
                <Badge label={`Energy: ${lastMessage.avg_energy.toFixed(2)}`} color="cyan" />
              )}
            </div>
          </div>
        ) : (
          <div className="h-24 flex items-center justify-center text-slate-500 italic">
            No voice data received yet. Press PTT to speak.
          </div>
        )}
      </div>

      {/* History List */}
      <div className="flex-1 flex flex-col min-h-0 bg-slate-900/50 rounded-xl border border-slate-800 overflow-hidden">
         <div className="p-4 border-b border-slate-800 bg-slate-900/80">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Transcript History</h3>
         </div>
         
         <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {transcripts.length > 0 ? (
                transcripts.map((msg) => (
                    <div key={msg.id} className="flex gap-4 p-3 rounded-lg hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-800">
                        <div className="flex-shrink-0 w-16 pt-1">
                            <div className="text-[10px] text-slate-500 font-mono">
                                {new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second:'2-digit' })}
                            </div>
                        </div>
                        <div className="flex-1 space-y-1">
                            <div className="text-sm text-slate-300">{msg.text}</div>
                            <div className="flex gap-2">
                                {msg.avg_pitch_hz && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">
                                        Pitch: {msg.avg_pitch_hz.toFixed(0)}Hz
                                    </span>
                                )}
                                {msg.avg_energy && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">
                                        Energy: {msg.avg_energy.toFixed(2)}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                ))
            ) : (
                <div className="text-center py-8 text-xs text-slate-600">
                    History is empty.
                </div>
            )}
         </div>
      </div>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: 'blue' | 'red' | 'slate' | 'cyan' }) {
  const colors = {
    blue: 'bg-blue-900/30 text-blue-300 border-blue-800',
    red: 'bg-red-900/30 text-red-300 border-red-800',
    slate: 'bg-slate-800 text-slate-400 border-slate-700',
    cyan: 'bg-cyan-900/30 text-cyan-300 border-cyan-800',
  };

  return (
    <span className={`text-xs px-2 py-1 rounded-md border font-medium ${colors[color]}`}>
      {label}
    </span>
  );
}

