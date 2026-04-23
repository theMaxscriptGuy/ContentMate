import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const SITE_URL = "https://www.contentmatepro.com";
const OG_IMAGE = "/contentmatepro-logo.png";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "ContentMatePro",
  description:
    "ContentMatePro helps creators analyze YouTube channels, uncover content gaps, and generate smarter video, shorts, and strategy ideas with AI.",
  applicationName: "ContentMatePro",
  keywords: [
    "YouTube channel analysis",
    "YouTube SEO",
    "content strategy",
    "creator tools",
    "AI content ideas",
    "YouTube transcript analysis",
    "shorts ideas",
    "video ideation"
  ],
  alternates: {
    canonical: "/"
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    title: "ContentMatePro",
    description:
      "Analyze YouTube channels, find content opportunities, and turn channel evidence into videos, shorts, and strategy plans.",
    siteName: "ContentMatePro",
    images: [
      {
        url: OG_IMAGE,
        width: 1254,
        height: 1254,
        alt: "ContentMatePro logo"
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: "ContentMatePro",
    description:
      "AI-powered YouTube channel analysis, content ideation, and creator strategy.",
    images: [OG_IMAGE]
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1
    }
  }
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
