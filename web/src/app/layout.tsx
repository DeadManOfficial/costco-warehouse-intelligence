import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DEADMAN // Costco Intelligence",
  description: "FREE database of 643 US Costco locations + Markdown Hunter deal scanner. Find hidden clearance deals with price code intelligence.",
  keywords: ["costco", "warehouse", "finder", "deals", "markdown", "clearance", "price codes", ".97", "death star"],
  openGraph: {
    title: "DEADMAN // Costco Intelligence",
    description: "643 US warehouses + Markdown Hunter deal scanner",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-950 text-white`}
      >
        {children}
      </body>
    </html>
  );
}
