import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';
import { Providers } from '@/providers/providers';

export const metadata: Metadata = {
  title: 'MadHacks',
  description: 'AI-powered audio processing platform',
};

type RootLayoutProps = {
  children: ReactNode;
};

/**
 * Root layout component for the Next.js application.
 *
 * Wraps all pages with global providers (React Query) and applies global styles.
 * Provides the HTML structure and body styling for the entire application.
 *
 * @param props - Component props.
 * @param props.children - React node containing page content to render.
 */
export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="background-gradient-wrapper" aria-hidden="true">
          <div className="blob blob-yellow" />
          <div className="blob blob-green" />
          <div className="blob blob-blue" />
        </div>
        <div className="background-noise" aria-hidden="true" />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
