import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const forwardedHost = requestHeaders.get("x-forwarded-host");
  const host = forwardedHost ?? requestHeaders.get("host") ?? "localhost";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.includes("localhost") ? "http" : "https");
  const safeHost = /^[a-z0-9.-]+(?::\d+)?$/i.test(host) ? host : "localhost";
  const origin = `${protocol === "http" ? "http" : "https"}://${safeHost}`;
  const description = "Discover Ethiopian live music, document what was played, and preserve the stories behind every performance.";

  return {
    metadataBase: new URL(origin),
    title: {
      default: "Zema Archive — Ethiopian live music, remembered",
      template: "%s · Zema Archive",
    },
    description,
    applicationName: "Zema Archive",
    keywords: ["Ethiopian music", "live music", "concerts", "setlists", "Addis Ababa", "Ethio-jazz"],
    openGraph: {
      type: "website",
      title: "Zema Archive",
      description,
      images: [{ url: `${origin}/og.png`, width: 1200, height: 630, alt: "Zema Archive — Every stage has a story." }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Zema Archive",
      description,
      images: [`${origin}/og.png`],
    },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f4efe3",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
