import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "小红书舆情监控",
  description: "实时监控小红书品牌舆情，情感分析与趋势追踪",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className="h-full dark">
      <body className="min-h-full bg-[#09090b] text-[#f4f4f5] antialiased">
        {children}
      </body>
    </html>
  );
}
