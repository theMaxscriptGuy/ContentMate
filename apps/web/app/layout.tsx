import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ContentMate",
  description: "AI-powered YouTube channel analysis and content ideation"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
