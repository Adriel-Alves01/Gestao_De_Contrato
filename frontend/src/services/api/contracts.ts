import { apiFetch } from "@/services/api/client"
import type { ContractAttachment, ContractSummary } from "@/types/contracts"

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
  numero_contrato?: string | null
  empresa_contratante?: string
  empresa_contratada?: string
  cnpj_empresa_contratada?: string
  cnpj_empresa_contratante?: string
}

export interface ContractUpdatePayload {
  title?: string
  description?: string
  total_value?: number
  manager_id?: number
  start_date?: string
  end_date?: string
  status?: "ACTIVE" | "CLOSED"
  numero_contrato?: string | null
  empresa_contratante?: string
  empresa_contratada?: string
  cnpj_empresa_contratada?: string
  cnpj_empresa_contratante?: string
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

export interface ContractExtractionResult {
  title?: string | null
  description?: string | null
  start_date?: string | null
  end_date?: string | null
  total_value?: number | null
  parties?: string | string[] | null
  numero_contrato?: string | null
  empresa_contratante?: string | null
  empresa_contratada?: string | null
  cnpj_empresa_contratada?: string | null
  cnpj_empresa_contratante?: string | null
}

export async function extractContractFromPdf(
  file: File
): Promise<ContractExtractionResult> {
  const formData = new FormData()
  formData.append("file", file)

  return apiFetch<ContractExtractionResult>(
    "/api/v1/contracts/extract-from-pdf/",
    {
      method: "POST",
      body: formData,
    }
  )
}

export async function createContract(payload: ContractCreatePayload): Promise<ContractSummary> {
  return apiFetch<ContractSummary>("/api/v1/contracts/", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function uploadContractAttachments(
  contractId: number,
  files: File[]
): Promise<void> {
  const formData = new FormData()
  for (const file of files) {
    formData.append("files", file)
  }
  await apiFetch<unknown>(`/api/v1/contracts/${contractId}/attachments/`, {
    method: "POST",
    body: formData,
  })
}

export async function listContractAttachments(
  contractId: number
): Promise<ContractAttachment[]> {
  return apiFetch<ContractAttachment[]>(
    `/api/v1/contracts/${contractId}/attachments/list/`
  )
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
