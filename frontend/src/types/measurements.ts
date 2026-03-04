export type MeasurementStatus = "PENDING" | "APPROVED" | "REJECTED"

export interface MeasurementSummary {
  id: number
  contract: number
  created_by: number | null
  description: string
  value: string
  status: MeasurementStatus
  approved_at: string | null
  rejected_at: string | null
  created_at: string
  updated_at: string
}
