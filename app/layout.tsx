import type { Metadata } from "next";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "SOURCERY",
  description: "Verified Supplier Search — every claim sourced, every field scored.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600&family=Geist+Mono:wght@400;500&display=swap"
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=localStorage.getItem('theme'),d=window.matchMedia('(prefers-color-scheme: dark)').matches;if(t==='dark'||(t!=='light'&&d))document.documentElement.classList.add('dark')})()`,
          }}
        />
      </head>
      <body className="min-h-screen antialiased" style={{ backgroundColor: "var(--bg)", color: "var(--text)" }}>
        <header
          className="sticky top-0 z-50 border-b"
          style={{
            backgroundColor: "var(--surface)",
            borderColor: "var(--border)",
            boxShadow: "0 1px 0 var(--border-subtle)",
          }}
        >
          <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2.5 group" aria-label="SOURCERY home">
              {/* Wordmark */}
              <span
                className="text-sm font-semibold tracking-[0.12em] uppercase"
                style={{ color: "var(--text)", letterSpacing: "0.12em" }}
              >
                SOURCERY
              </span>
              <span
                className="text-xs px-1.5 py-0.5 rounded font-mono-data font-medium"
                style={{
                  backgroundColor: "var(--accent-subtle)",
                  color: "var(--accent)",
                  fontSize: "10px",
                  letterSpacing: "0.04em",
                }}
              >
                BETA
              </span>
            </a>

            <nav className="flex items-center gap-1">
              <a
                href="/providers"
                className="text-xs px-3 py-1.5 rounded-md transition-colors hover:bg-[var(--bg-muted)]"
                style={{ color: "var(--text-muted)" }}
              >
                Providers
              </a>
              <ThemeToggle />
            </nav>
          </div>
        </header>

        <main>{children}</main>
      </body>
    </html>
  );
}
