import { env } from "@/config/env"
import { getAccessToken, refreshAccessToken } from "@/services/api/auth"

interface ApiErrorPayload {
  error?: {
    detail?: unknown
  }
  detail?: unknown
}

function getThrottleWaitSeconds(response: Response, detailText?: string | null) {
  const retryAfter = response.headers.get("Retry-After")
  if (retryAfter) {
    const retryAfterSeconds = Number(retryAfter)
    if (!Number.isNaN(retryAfterSeconds) && retryAfterSeconds > 0) {
      return Math.ceil(retryAfterSeconds)
    }
  }

  if (!detailText) {
    return null
  }

  const matched = detailText.match(/(\d+)\s*seconds?/i)
  if (!matched) {
    return null
  }

  const parsed = Number(matched[1])
  if (Number.isNaN(parsed) || parsed <= 0) {
    return null
  }

  return parsed
}

export class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiRequestError"
    this.status = status
  }
}

function normalizeErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => normalizeErrorDetail(item))
      .filter((item): item is string => Boolean(item))
    return messages.length ? messages.join(" | ") : null
  }

  if (detail && typeof detail === "object") {
    const values = Object.values(detail as Record<string, unknown>)
      .map((value) => normalizeErrorDetail(value))
      .filter((item): item is string => Boolean(item))
    return values.length ? values.join(" | ") : null
  }

  return null
}

function getCsrfTokenFromCookie(): string | null {
  if (typeof document === "undefined") {
    return null
  }

  const csrfCookie = document.cookie
    .split(";")
    .map((cookieItem) => cookieItem.trim())
    .find((cookieItem) => cookieItem.startsWith("csrftoken="))

  if (!csrfCookie) {
    return null
  }

  return decodeURIComponent(csrfCookie.split("=")[1] ?? "")
}

let refreshInFlight: Promise<boolean> | null = null

async function refreshAccessTokenSafely(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = refreshAccessToken().finally(() => {
      refreshInFlight = null
    })
  }

  return refreshInFlight
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase()
  const buildHeaders = () => {
    const headers = new Headers(init?.headers)
    const hasBody = init?.body !== undefined && init?.body !== null

    if (hasBody && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json")
    }

    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      const csrfToken = getCsrfTokenFromCookie()
      if (csrfToken && !headers.has("X-CSRFToken")) {
        headers.set("X-CSRFToken", csrfToken)
      }
    }

    const accessToken = getAccessToken()
    if (accessToken && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${accessToken}`)
    }

    return headers
  }

  const runRequest = async () => {
    return fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      method,
      credentials: "include",
      headers: buildHeaders(),
      cache: "no-store",
    })
  }

  let response: Response

  try {
    response = await runRequest()
  } catch {
    throw new ApiRequestError(
      `Falha de conexão com a API em ${env.apiBaseUrl}. Verifique se o backend está ativo e liberado no CORS.`,
      0
    )
  }

  if (response.status === 401 && !new Headers(init?.headers).has("Authorization")) {
    const refreshed = await refreshAccessTokenSafely()
    if (refreshed) {
      try {
        response = await runRequest()
      } catch {
        throw new ApiRequestError(
          `Falha de conexão com a API em ${env.apiBaseUrl}. Verifique se o backend está ativo e liberado no CORS.`,
          0
        )
      }
    }
  }

  if (!response.ok) {
    let errorMessage = "Erro ao comunicar com a API"
    let normalizedDetail: string | null = null

    try {
      const payload = (await response.json()) as ApiErrorPayload
      normalizedDetail =
        normalizeErrorDetail(payload.error?.detail) ??
        normalizeErrorDetail(payload.detail)

      if (normalizedDetail) {
        errorMessage = normalizedDetail
      }
    } catch {
      errorMessage = `Erro HTTP ${response.status}`
    }

    if (response.status === 429) {
      const waitSeconds = getThrottleWaitSeconds(response, normalizedDetail)
      if (waitSeconds) {
        errorMessage = `Muitas requisições em sequência. Tente novamente em ${waitSeconds} segundos.`
      } else {
        errorMessage = "Muitas requisições em sequência. Aguarde alguns instantes e tente novamente."
      }
    }

    throw new ApiRequestError(errorMessage, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const responseContentType = response.headers.get("content-type") ?? ""
  const hasJsonResponse = responseContentType.includes("application/json")

  if (!hasJsonResponse) {
    return undefined as T
  }

  const responseText = await response.text()
  if (!responseText) {
    return undefined as T
  }

  return JSON.parse(responseText) as T
}
