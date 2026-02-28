import "./globals.css";
import { Providers } from "./providers";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});
const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className={`${inter.variable} ${spaceGrotesk.variable} ${jetBrainsMono.variable} font-sans`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
