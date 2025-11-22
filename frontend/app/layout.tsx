import type { Metadata } from 'next';
import './globals.css';
import { Providers } from '../providers/providers';

export const metadata: Metadata = {
  title: 'MadHacks',
  description: 'AI-powered audio processing platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
