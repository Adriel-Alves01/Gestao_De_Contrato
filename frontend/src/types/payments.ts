export type PaymentStatus = "PENDING" | "PAID" | "FAILED"

export interface PaymentSummary {
  id: number
  contract: number
  contract_title: string | null
  measurement: number
  measurement_description: string | null
  created_by: number | null
  amount: string
  status: PaymentStatus
  paid_at: string | null
  numero_nota_fiscal: string | null
  data_emissao_nota: string | null
  valor_nota_fiscal: string | null
  anexo_nota_fiscal: string | null
  anexo_nota_fiscal_url: string | null
  created_at: string
  updated_at: string
}

export interface NfExtractedData {
  numero_nota_fiscal: string | null
  data_emissao_nota: string | null
  valor_nota_fiscal: number | null
}
