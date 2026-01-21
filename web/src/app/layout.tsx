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
  title: "Costco Warehouse Intelligence",
  description: "FREE database of 643 US Costco locations with GPS, hours, services & markdown deals",
  keywords: ["costco", "warehouse", "finder", "deals", "markdown", "clearance"],
  openGraph: {
    title: "Costco Warehouse Intelligence",
    description: "Find any Costco warehouse + hidden markdown deals",
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
