import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Script from 'next/script';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Graph RAG System',
  description: 'Science-Based Training Recommendation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* D3.js v5 */}
        <Script
          src="https://d3js.org/d3.v5.min.js"
          strategy="beforeInteractive"
        />
        {/* Popoto.js */}
        <Script
          src="https://unpkg.com/popoto@2.0.0/dist/popoto.min.js"
          strategy="beforeInteractive"
        />
        <link
          rel="stylesheet"
          href="https://unpkg.com/popoto@2.0.0/dist/popoto.min.css"
        />
      </head>
      <body className={inter.className}>
        {children}
      </body>
    </html>
  );
}
