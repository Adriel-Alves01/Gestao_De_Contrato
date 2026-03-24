export type ContractStatus = "ACTIVE" | "CLOSED"

export interface ContractAttachment {
  id: number
  file: string
  file_name: string | null
  uploaded_by_name: string
  created_at: string
}

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
  numero_contrato: string | null
  empresa_contratante: string
  empresa_contratada: string
  cnpj_empresa_contratada: string
  cnpj_empresa_contratante: string
  manager: ContractManager | null
  created_at: string
  updated_at: string
}
