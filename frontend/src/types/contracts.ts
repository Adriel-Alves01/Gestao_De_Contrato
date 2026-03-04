export type ContractStatus = "ACTIVE" | "CLOSED"

export interface ContractManager {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
}

export interface ContractSummary {
  id: number
  title: string
  description: string
  total_value: string
  remaining_balance: string
  start_date: string
  end_date: string
  status: ContractStatus
  manager: ContractManager | null
  created_at: string
  updated_at: string
}
