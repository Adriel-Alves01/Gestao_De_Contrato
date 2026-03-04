import { env } from "@/config/env"

const ACCESS_TOKEN_KEY = "clm_access_token"
const REFRESH_TOKEN_KEY = "clm_refresh_token"

interface TokenPairResponse {
  access: string
  refresh: string
}

interface AccessTokenResponse {
  access: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface AuthMeResponse {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_superuser: boolean
  groups: string[]
}

function parseErrorMessage(payload: unknown): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === "string") {
      return detail
    }
  }

  return "Não foi possível autenticar. Verifique usuário e senha."
}

function buildHttpError(message: string, status: number): Error {
  const error = new Error(message)
  ;(error as Error & { status?: number }).status = status
  return error
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }

  return window.localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }

  return window.localStorage.getItem(REFRESH_TOKEN_KEY)
}

function setAccessToken(access: string) {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, access)
}

function setTokens(tokens: TokenPairResponse) {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access)
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh)
}

export function clearTokens() {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  window.localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export async function login(payload: LoginPayload): Promise<void> {
  const response = await fetch(`${env.apiBaseUrl}/api/token/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    credentials: "include",
    cache: "no-store",
  })

  if (!response.ok) {
    let message = "Não foi possível autenticar. Verifique usuário e senha."

    try {
      const payload = (await response.json()) as unknown
      message = parseErrorMessage(payload)
    } catch {
      message = `Erro HTTP ${response.status}`
    }

    throw buildHttpError(message, response.status)
  }

  const tokens = (await response.json()) as TokenPairResponse
  setTokens(tokens)
}

export async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken()
  if (!refresh) {
    clearTokens()
    return false
  }

  try {
    const response = await fetch(`${env.apiBaseUrl}/api/token/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh }),
      credentials: "include",
      cache: "no-store",
    })

    if (!response.ok) {
      clearTokens()
      return false
    }

    const payload = (await response.json()) as AccessTokenResponse
    if (!payload.access) {
      clearTokens()
      return false
    }

    setAccessToken(payload.access)
    return true
  } catch {
    clearTokens()
    return false
  }
}

export async function getCurrentUser(): Promise<AuthMeResponse> {
  return fetch(`${env.apiBaseUrl}/api/v1/auth/me/`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
    },
    credentials: "include",
    cache: "no-store",
  }).then(async (response) => {
    if (!response.ok) {
      let message = "Não foi possível carregar o usuário autenticado."

      try {
        const payload = (await response.json()) as unknown
        message = parseErrorMessage(payload)
      } catch {
        message = `Erro HTTP ${response.status}`
      }

      throw buildHttpError(message, response.status)
    }

    return (await response.json()) as AuthMeResponse
  })
}
