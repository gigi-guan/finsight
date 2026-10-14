import type { Metadata } from "next";
import { Cormorant_Garamond, IBM_Plex_Mono, Source_Sans_3 } from "next/font/google";

import AppNav from "@/components/app-nav";

import "./globals.css";

const serif = Cormorant_Garamond({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const sans = Source_Sans_3({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "FinSight",
  description: "Personal financial intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <div className="frame">
          <AppNav />
          <div className="canvas">{children}</div>
        </div>
      </body>
    </html>
  );
}
