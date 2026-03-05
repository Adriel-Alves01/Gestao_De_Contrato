import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { RouteAuthGuard } from "@/components/auth/route-auth-guard";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Gestão de Contratos",
  description: "Painel web para operação e acompanhamento de contratos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <RouteAuthGuard>{children}</RouteAuthGuard>
      </body>
    </html>
  );
}
