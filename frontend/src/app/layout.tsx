import "@/styles/globals.css";

import { type Metadata } from "next";
import { Host_Grotesk, Cedarville_Cursive } from "next/font/google";

export const metadata: Metadata = {
  title: "horizon at sea",
  description: "horizon at sea",
  icons: [
    {
      rel: "icon",
      url: "data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🖥️</text></svg>",
    },
  ],
  openGraph: {
    images: [
      {
        url: "/og.jpg",
        width: 1200,
        height: 630,
        alt: "Horizon at Sea Collection",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: ["/og.jpg"],
  },
};

const hostGrotesk = Host_Grotesk({
  subsets: ["latin"],
  variable: "--font-host-grotesk",
});

const cedarvilleCursive = Cedarville_Cursive({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-cedarville-cursive",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${hostGrotesk.variable} ${cedarvilleCursive.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
