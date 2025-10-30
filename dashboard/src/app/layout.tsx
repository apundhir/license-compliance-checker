import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";

import "./globals.css";

import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { AuthProvider } from "@/contexts/AuthContext";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.APP_URL
      ? `${process.env.APP_URL}`
      : process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : `http://localhost:${process.env.PORT || 3000}`
  ),
  title: "License Compliance Checker",
  description:
    "Professional license compliance dashboard with AI/ML detection, SBOM generation, and policy management.",
  alternates: {
    canonical: "/"
  },
  openGraph: {
    url: "/",
    title: "License Compliance Checker",
    description:
      "Professional license compliance dashboard with AI/ML detection, SBOM generation, and policy management.",
    type: "website"
  },
  twitter: {
    card: "summary_large_image",
    title: "License Compliance Checker",
    description:
      "Professional license compliance dashboard with AI/ML detection, SBOM generation, and policy management."
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={GeistSans.className}>
        <QueryProvider>
          <AuthProvider>
            <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
              {children}
              <Toaster richColors position="top-right" />
            </ThemeProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
