import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "arXiv Digest · Research Radar",
  description: "Manage your daily arXiv paper digest topics and keywords",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  );
}
