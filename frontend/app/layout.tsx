import type { Metadata } from 'next';
import './globals.css';

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
      <body className="antialiased">{children}</body>
    </html>
  );
}
