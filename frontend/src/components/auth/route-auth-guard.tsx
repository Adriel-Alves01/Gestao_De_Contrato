"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { clearTokens, getAccessToken, getCurrentUser } from "@/services/api/auth"

interface RouteAuthGuardProps {
  children: React.ReactNode
}

export function RouteAuthGuard({ children }: RouteAuthGuardProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)

  useEffect(() => {
    const isPublicRoute = pathname === "/login"

    if (isPublicRoute) {
      setIsCheckingAuth(false)
      return
    }

    const accessToken = getAccessToken()
    if (!accessToken) {
      router.replace("/login")
      setIsCheckingAuth(false)
      return
    }

    const validateSession = async () => {
      try {
        await getCurrentUser()
        setIsCheckingAuth(false)
      } catch {
        clearTokens()
        router.replace("/login")
      }
    }

    void validateSession()
  }, [pathname, router])

  if (isCheckingAuth) {
    return null
  }

  return <>{children}</>
}
