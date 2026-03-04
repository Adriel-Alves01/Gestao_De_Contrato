import { apiFetch } from "@/services/api/client"
import type { ContractSummary } from "@/types/contracts"

export interface ContractListResponse {
  count: number
  next: string | null
  previous: string | null
  results: ContractSummary[]
}

export interface ContractCreatePayload {
  title: string
  description?: string
  total_value: number
  manager_id?: number
  start_date: string
  end_date: string
  status?: "ACTIVE" | "CLOSED"
}

export interface ContractUpdatePayload {
  title?: string
  description?: string
  total_value?: number
  manager_id?: number
  start_date?: string
  end_date?: string
  status?: "ACTIVE" | "CLOSED"
}

interface ContractListQueryOptions {
  pageSize?: number
  managerId?: number
}

function buildContractListQuery(
  page: number,
  options?: ContractListQueryOptions
) {
  const params = new URLSearchParams()
  params.set("page", String(page))

  if (options?.pageSize) {
    params.set("page_size", String(options.pageSize))
  }

  if (options?.managerId) {
    params.set("manager", String(options.managerId))
  }

  return params.toString()
}

export async function listContracts(pageSize = 5): Promise<ContractSummary[]> {
  const data = await apiFetch<ContractListResponse>(
    `/api/v1/contracts/?page_size=${pageSize}`
  )
  return data.results
}

export async function listContractsPaginated(
  page = 1,
  options?: ContractListQueryOptions
): Promise<ContractListResponse> {
  const query = buildContractListQuery(page, options)
  return apiFetch<ContractListResponse>(`/api/v1/contracts/?${query}`)
}

export async function createContract(payload: ContractCreatePayload): Promise<ContractSummary> {
  return apiFetch<ContractSummary>("/api/v1/contracts/", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function getContract(contractId: number): Promise<ContractSummary> {
  return apiFetch<ContractSummary>(`/api/v1/contracts/${contractId}/`)
}

export async function updateContract(
  contractId: number,
  payload: ContractUpdatePayload
): Promise<ContractSummary> {
  return apiFetch<ContractSummary>(`/api/v1/contracts/${contractId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export async function deleteContract(contractId: number): Promise<void> {
  await apiFetch<void>(`/api/v1/contracts/${contractId}/`, {
    method: "DELETE",
  })
}

export async function closeContract(contractId: number): Promise<ContractSummary> {
  return apiFetch<ContractSummary>(`/api/v1/contracts/${contractId}/close/`, {
    method: "POST",
  })
}
