import { apiFetch } from "@/services/api/client"
import type { NfExtractedData, PaymentSummary } from "@/types/payments"

export interface PaymentListResponse {
  count: number
  next: string | null
  previous: string | null
  results: PaymentSummary[]
}

export interface PaymentActionResponse {
  detail: string
  id: number
  status: "PAID" | "FAILED"
  contract_remaining_balance?: string
}

function normalizePaymentListResponse(
  data: PaymentListResponse | PaymentSummary[]
): PaymentListResponse {
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

export async function listPaymentsPaginated(page = 1): Promise<PaymentListResponse> {
  const data = await apiFetch<PaymentListResponse | PaymentSummary[]>(
    `/api/v1/payments/?page=${page}`
  )

  return normalizePaymentListResponse(data)
}

export async function listPaymentsByContract(
  contractId: number
): Promise<PaymentSummary[]> {
  const data = await apiFetch<PaymentListResponse | PaymentSummary[]>(
    `/api/v1/payments/?contract=${contractId}`
  )

  return normalizePaymentListResponse(data).results
}

export async function getPayment(paymentId: number): Promise<PaymentSummary> {
  return apiFetch<PaymentSummary>(`/api/v1/payments/${paymentId}/`)
}

export async function markPaymentAsPaid(
  paymentId: number,
  nfFormData?: FormData
): Promise<PaymentActionResponse> {
  return apiFetch<PaymentActionResponse>(`/api/v1/payments/${paymentId}/mark-as-paid/`, {
    method: "POST",
    body: nfFormData ?? undefined,
  })
}

export async function markPaymentAsFailed(
  paymentId: number
): Promise<PaymentActionResponse> {
  return apiFetch<PaymentActionResponse>(`/api/v1/payments/${paymentId}/mark-as-failed/`, {
    method: "POST",
  })
}

export async function extractNfData(file: File): Promise<NfExtractedData> {
  const formData = new FormData()
  formData.append("arquivo_nf", file)
  return apiFetch<NfExtractedData>("/api/v1/payments/extract-nf/", {
    method: "POST",
    body: formData,
  })
}
