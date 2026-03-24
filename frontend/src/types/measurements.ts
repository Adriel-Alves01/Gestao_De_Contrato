export type MeasurementStatus = "PENDING" | "APPROVED" | "REJECTED"

export interface MeasurementSummary {
  id: number
  contract: number
  contract_title: string | null
  created_by: number | null
  description: string
  value: string
  start_date: string | null
  end_date: string | null
  status: MeasurementStatus
  approved_at: string | null
  approved_by_name: string | null
  rejected_at: string | null
  rejected_by_name: string | null
  created_at: string
  updated_at: string
}
