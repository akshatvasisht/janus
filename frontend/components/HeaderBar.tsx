import React from 'react';
import Link from 'next/link';
import { ConnectionStatus } from '../types/janus';
import { Badge } from './ui/badge';
import { Wifi, Activity } from 'lucide-react';

type NavigationLink = {
  href: string;
  label: string;
};

type HeaderBarProps = {
  status: ConnectionStatus;
  lastError?: string | null;
  links?: NavigationLink[];
};

export default function HeaderBar({
  status,
  lastError,
  links = [],
}: HeaderBarProps) {
  const statusText = {
    connected: 'Connected',
    connecting: 'Connecting...',
    disconnected: 'Disconnected',
  }[status];

  const isConnected = status === 'connected';

  return (
    <header className="border-b-4 border-black bg-white">
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-start gap-0 flex-col">
          <h1 className="tracking-wider text-2xl font-black text-black uppercase leading-none">
            Janus
          </h1>
          <h4 className="text-sm font-bold text-muted-foreground uppercase leading-tight">
            Semantic Audio Codec
          </h4>
        </div>
        <div className="flex items-center gap-4 h-full">
          {isConnected && (
            <div className="flex items-center gap-2">
              <Wifi className="size-4 text-black" />
              <span className="text-black font-bold text-sm">Connected</span>
            </div>
          )}
          <Badge
            variant="outline"
            className={
              isConnected
                ? 'border-2 border-black bg-green-400 text-black font-bold rounded-none'
                : status === 'connecting'
                ? 'border-2 border-black bg-yellow-400 text-black font-bold rounded-none'
                : 'border-2 border-black bg-red-500 text-white font-bold rounded-none'
            }
          >
            <Activity className="size-3 mr-1" />
            {status === 'connected' ? 'Active' : statusText}
          </Badge>
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-xs font-bold underline text-black hover:text-slate-600"
            >
              {link.label}
            </Link>
          ))}
          {lastError && (
            <span
              className="text-xs text-red-600 font-mono max-w-[200px] truncate"
              title={lastError}
            >
              {lastError}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
