"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  ClipboardList,
  FileText,
  LayoutDashboard,
  Settings,
  Wallet,
} from "lucide-react"

import { AppHeader } from "@/components/layout/app-header"

interface AppShellProps {
  children: React.ReactNode
}

const navigationItems = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Contratos", icon: FileText, href: "/contracts" },
  { label: "Medições", icon: ClipboardList, href: "/measurements" },
  { label: "Pagamentos", icon: Wallet, href: "/payments" },
  { label: "Configurações", icon: Settings, href: "#" },
]

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-secondary/45">
      <AppHeader />

      <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-6 px-6 py-6 md:grid-cols-[220px_1fr]">
        <aside className="rounded-2xl border bg-card p-3 shadow-sm">
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon
              const isActive = item.href !== "#" && pathname === item.href

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={[
                    "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  ].join(" ")}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </aside>

        <main>{children}</main>
      </div>
    </div>
  )
}
