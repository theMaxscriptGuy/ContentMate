import type { Metadata } from "next";

import AdminClient from "./AdminClient";

export const metadata: Metadata = {
  title: "Workspace | ContentMatePro",
  description: "Internal workspace page.",
  robots: {
    index: false,
    follow: false,
    googleBot: {
      index: false,
      follow: false,
      "max-image-preview": "none",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export default function AdminPage() {
  return <AdminClient />;
}
