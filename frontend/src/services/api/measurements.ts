import { apiFetch } from "@/services/api/client"
import type { MeasurementSummary } from "@/types/measurements"

export interface MeasurementListResponse {
  count: number
  next: string | null
  previous: string | null
  results: MeasurementSummary[]
}

export interface MeasurementCreatePayload {
  contract: number
  description?: string
  value: number
}

export interface MeasurementUpdatePayload {
  contract?: number
  description?: string
  value?: number
}

export interface MeasurementActionResponse {
  detail: string
  id: number
  status: "APPROVED" | "REJECTED"
}

interface MeasurementListQueryOptions {
  pageSize?: number
  contractId?: number
}

function buildMeasurementListQuery(
  page: number,
  options?: MeasurementListQueryOptions
) {
  const params = new URLSearchParams()
  params.set("page", String(page))
  params.set("page_size", String(options?.pageSize ?? 15))

  if (options?.contractId) {
    params.set("contract", String(options.contractId))
  }

  return params.toString()
}

function normalizeMeasurementListResponse(
  data: MeasurementListResponse | MeasurementSummary[]
): MeasurementListResponse {
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data,
    }
  }

  return {
    count: data.count ?? 0,
    next: data.next ?? null,
    previous: data.previous ?? null,
    results: data.results ?? [],
  }
}

export async function listMeasurementsPaginated(
  page = 1,
  options?: MeasurementListQueryOptions
): Promise<MeasurementListResponse> {
  const query = buildMeasurementListQuery(page, options)
  const data = await apiFetch<MeasurementListResponse | MeasurementSummary[]>(
    `/api/v1/measurements/?${query}`
  )

  return normalizeMeasurementListResponse(data)
}

export async function listMeasurementsByContract(
  contractId: number
): Promise<MeasurementSummary[]> {
  const data = await apiFetch<MeasurementListResponse | MeasurementSummary[]>(
    `/api/v1/measurements/?contract=${contractId}`
  )

  return normalizeMeasurementListResponse(data).results
}

export async function getMeasurement(measurementId: number): Promise<MeasurementSummary> {
  return apiFetch<MeasurementSummary>(`/api/v1/measurements/${measurementId}/`)
}

export async function createMeasurement(
  payload: MeasurementCreatePayload
): Promise<MeasurementSummary> {
  return apiFetch<MeasurementSummary>("/api/v1/measurements/", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function updateMeasurement(
  measurementId: number,
  payload: MeasurementUpdatePayload
): Promise<MeasurementSummary> {
  return apiFetch<MeasurementSummary>(`/api/v1/measurements/${measurementId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export async function deleteMeasurement(measurementId: number): Promise<void> {
  await apiFetch<void>(`/api/v1/measurements/${measurementId}/`, {
    method: "DELETE",
  })
}

export async function approveMeasurement(
  measurementId: number
): Promise<MeasurementActionResponse> {
  return apiFetch<MeasurementActionResponse>(
    `/api/v1/measurements/${measurementId}/approve/`,
    {
      method: "POST",
    }
  )
}

export async function rejectMeasurement(
  measurementId: number
): Promise<MeasurementActionResponse> {
  return apiFetch<MeasurementActionResponse>(
    `/api/v1/measurements/${measurementId}/reject/`,
    {
      method: "POST",
    }
  )
}
