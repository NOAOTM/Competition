import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "真知 Agent", description: "面向大学生的学习与科研助手" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
