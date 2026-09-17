import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ReviewProvider } from "@/lib/review-context";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "PatchCourt — Evidence-Gated AI Code Review",
  description: "Multi-agent AI PR review with tiered evidence, debate, and defense-grade verdicts",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark ${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ReviewProvider>{children}</ReviewProvider>
      </body>
    </html>
  );
}