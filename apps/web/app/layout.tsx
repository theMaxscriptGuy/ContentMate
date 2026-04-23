import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const SITE_URL = "https://www.contentmatepro.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "ContentMatePro",
  description: "AI-powered YouTube channel analysis and content ideation"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
