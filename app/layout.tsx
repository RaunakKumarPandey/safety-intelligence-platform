import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "./components/ThemeProvider";
import AppLayout from "./components/AppLayout";

export const metadata: Metadata = {
  title: "SurakshaSetu - Safety Intelligence Platform (Oil India Limited)",
  description: "AI-powered industrial safety intelligence and risk detection system built for Oil India Limited (SIH26165)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50 antialiased dark:bg-[#06120f]">
        <ThemeProvider>
          <AppLayout>{children}</AppLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}