import type { Metadata } from "next";
import { DM_Sans, Playfair_Display } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const playfairDisplay = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Skeldir - See exactly where your ad budget is wasted",
  description: "Skeldir shows you the gap between what ad platforms claim and what actually hits your bank account—so you can move budget with confidence, not guesswork.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* Preload hero background images so they are fetched early and ready before hero paint */}
        <link rel="preload" as="image" href="/images/Background-2.png" />
        <link rel="preload" as="image" href="/images/Background%202%20Agencies.png" />
      </head>
      <body className={`${dmSans.variable} ${playfairDisplay.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
