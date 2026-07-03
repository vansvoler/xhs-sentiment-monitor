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
    <html lang="zh-CN" className="h-full">
      <body className="min-h-full bg-[#f4f6fa] text-[#1f2a44] antialiased">
        {children}
      </body>
    </html>
  );
}
