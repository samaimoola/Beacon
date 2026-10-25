import type { Metadata, Viewport } from 'next';
import { Fraunces, Inter } from 'next/font/google';
import './globals.css';

const display = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  axes: ['opsz', 'SOFT'],
  display: 'swap',
});

const ui = Inter({ subsets: ['latin'], variable: '--font-ui', display: 'swap' });

export const metadata: Metadata = {
  title: "Beacon — When the lights go out, your plan doesn't",
  description:
    'Beacon is a prototype storm-planning instrument (HackOHI/O 2026): simulated storm scenarios, modeled restoration ranges, and preparation guidance for an anonymized household.',
};

export const viewport: Viewport = {
  themeColor: '#0d2429',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${ui.variable}`}>
      <body>{children}</body>
    </html>
  );
}
