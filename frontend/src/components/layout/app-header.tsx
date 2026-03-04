"use client"

import Link from "next/link"
import { Bell, ChevronDown, UserCircle2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { clearTokens } from "@/services/api/auth"

export function AppHeader() {
  const router = useRouter()
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false)
  const accountMenuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!accountMenuRef.current) {
        return
      }

      const target = event.target
      if (target instanceof Node && !accountMenuRef.current.contains(target)) {
        setIsAccountMenuOpen(false)
      }
    }

    window.addEventListener("mousedown", handleOutsideClick)
    return () => {
      window.removeEventListener("mousedown", handleOutsideClick)
    }
  }, [])

  const handleLogout = () => {
    clearTokens()
    setIsAccountMenuOpen(false)
    router.push("/login")
  }

  return (
    <header className="border-b border-sidebar-border bg-sidebar-foreground text-sidebar backdrop-blur supports-[backdrop-filter]:bg-sidebar-foreground/95">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6">
        <div>
          <p className="text-xs uppercase tracking-wide text-sidebar/70">Gestão de Contratos</p>
          <h1 className="text-lg font-semibold tracking-tight text-sidebar">Painel Operacional</h1>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="border border-sidebar-border bg-sidebar text-sidebar-foreground">
            Ambiente Local
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            aria-label="Notificações"
            className="text-sidebar hover:bg-sidebar-primary/20 hover:text-sidebar"
          >
            <Bell className="h-4 w-4" />
          </Button>

          <div className="relative" ref={accountMenuRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAccountMenuOpen((previousState) => !previousState)}
              className="border-sidebar-border bg-sidebar-foreground/20 text-sidebar hover:bg-sidebar-primary/20 hover:text-sidebar"
            >
              <UserCircle2 className="h-4 w-4" />
              Minha Conta
              <ChevronDown className="h-4 w-4" />
            </Button>

            {isAccountMenuOpen ? (
              <div className="absolute right-0 z-50 mt-2 w-52 rounded-md border bg-card p-1 text-card-foreground shadow-md">
                <Link
                  href="#"
                  className="block rounded-sm px-3 py-2 text-sm text-card-foreground hover:bg-accent hover:text-accent-foreground"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  Minha conta
                </Link>
                <Link
                  href="#"
                  className="block rounded-sm px-3 py-2 text-sm text-card-foreground hover:bg-accent hover:text-accent-foreground"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  Informações pessoais
                </Link>
                <Link
                  href="#"
                  className="block rounded-sm px-3 py-2 text-sm text-card-foreground hover:bg-accent hover:text-accent-foreground"
                  onClick={() => setIsAccountMenuOpen(false)}
                >
                  Configurações
                </Link>
                <button
                  type="button"
                  className="block w-full rounded-sm px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/10"
                  onClick={handleLogout}
                >
                  Sair
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  )
}
