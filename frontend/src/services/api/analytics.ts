import { apiFetch } from "@/services/api/client"

export interface AnalyticsOverviewResponse {
  contracts: {
    total_contracts: number
    active_contracts: number
    closed_contracts: number
    total_value: string
    total_remaining: string
    avg_contract_value: string
    percentage_completed: string
  }
  measurements: {
    total_measurements: number
    pending_measurements: number
    approved_measurements: number
    rejected_measurements: number
    total_value: string
    approved_value: string
    pending_value: string
    avg_measurement_value: string
  }
  payments: {
    total_payments: number
    pending_payments: number
    paid_payments: number
    failed_payments: number
    total_amount: string
    paid_amount: string
    pending_amount: string
    avg_payment_amount: string
  }
  recent_activities: Array<{
    action: string
    user: string | null
    model_name: string
    object_id: number
    object_display: string
    timestamp: string
  }>
}

export async function getAnalyticsOverview(): Promise<AnalyticsOverviewResponse> {
  return apiFetch<AnalyticsOverviewResponse>("/api/v1/analytics/overview/")
}
