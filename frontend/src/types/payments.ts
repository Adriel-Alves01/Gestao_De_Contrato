export type PaymentStatus = "PENDING" | "PAID" | "FAILED"

export interface PaymentSummary {
  id: number
  contract: number
  measurement: number
  created_by: number | null
  amount: string
  status: PaymentStatus
  paid_at: string | null
  created_at: string
  updated_at: string
}
