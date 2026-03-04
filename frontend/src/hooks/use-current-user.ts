"use client"

import { useEffect, useState } from "react"

import { getCurrentUser, type AuthMeResponse } from "@/services/api/auth"

export function useCurrentUser() {
  const [user, setUser] = useState<AuthMeResponse | null>(null)
  const [isLoadingUser, setIsLoadingUser] = useState(true)

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const currentUser = await getCurrentUser()
        setUser(currentUser)
      } catch {
        setUser(null)
      } finally {
        setIsLoadingUser(false)
      }
    }

    void loadCurrentUser()
  }, [])

  const groups = user?.groups ?? []

  return {
    user,
    isLoadingUser,
    isFinancialUser: groups.includes("FINANCEIRO"),
  }
}
