import type { Metadata } from "next";

import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "Kanban AI Workspace",
  description: "Kanban and AI meeting task extraction workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const bootThemeScript = `
    (() => {
      try {
        const stored = window.localStorage.getItem("kanban-theme-mode");
        const mode = stored === "dark" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", mode);
      } catch {}
    })();
  `;

  return (
    <html
      lang="en"
      className="antialiased"
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: bootThemeScript }} />
      </head>
      <body suppressHydrationWarning>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
