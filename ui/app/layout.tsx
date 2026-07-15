import type { Metadata } from "next";
import { LoadingProvider } from "@/lib/contexts/loading-context";
import "./globals.scss";

export const metadata: Metadata = {
  title: "CSIS SmartAssist — BITS Pilani Goa",
  description:
    "AI-powered departmental assistant for the Computer Science & Information Systems Department at BITS Pilani, K K Birla Goa Campus. Instant access to syllabi, policies, prerequisites, and automated room reservations.",
  keywords: [
    "BITS Pilani",
    "CSIS",
    "Computer Science",
    "AI Assistant",
    "SmartAssist",
    "Goa Campus",
  ],
  authors: [{ name: "CSIS Department, BITS Pilani Goa" }],
};

import { JetBrains_Mono, Inter, Space_Grotesk } from "next/font/google";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${jetbrainsMono.variable} ${inter.variable} ${spaceGrotesk.variable}`}
        suppressHydrationWarning
      >
        <LoadingProvider>
          {children}
        </LoadingProvider>
      </body>
    </html>
  );
}
