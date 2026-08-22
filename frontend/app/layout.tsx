import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Navbar } from "@/components/navbar";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "BazaarPulse — Real-time Indian Market Intelligence",
  description:
    "Live e-commerce price tracking & AI sentiment analysis for the Indian market (Flipkart, Amazon.in).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`}>
        <ThemeProvider>
          <div className="flex min-h-screen flex-col">
            <Navbar />
            <main className="flex-1">{children}</main>
            <footer className="border-t py-6">
              <p className="text-center text-xs text-muted-foreground">
                BazaarPulse · Simulated real-time market intelligence · Data Analyst portfolio project
              </p>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
