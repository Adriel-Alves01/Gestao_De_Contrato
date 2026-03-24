"use client"

import Link from "next/link"
import { useEffect, useRef, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getMeasurement } from "@/services/api/measurements"
import {
  extractNfData,
  getPayment,
  markPaymentAsFailed,
  markPaymentAsPaid,
} from "@/services/api/payments"
import type { MeasurementSummary } from "@/types/measurements"
import type { PaymentSummary } from "@/types/payments"

interface PaymentDetailPageContentProps {
  paymentId: string
}

function formatMoney(value: string | number | null) {
  if (value === null || value === undefined) return "-"
  const parsedValue = Number(value)
  if (Number.isNaN(parsedValue)) return String(value)
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(parsedValue)
}

function formatDate(value: string | null) {
  if (!value) return "-"
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value)
  const parsedDate = dateOnly ? new Date(`${value}T00:00:00`) : new Date(value)
  if (Number.isNaN(parsedDate.getTime())) return value
  return new Intl.DateTimeFormat("pt-BR").format(parsedDate)
}

function formatPaymentStatusLabel(status: PaymentSummary["status"]) {
  if (status === "PAID") return "Pago"
  if (status === "FAILED") return "Falhou"
  return "Pendente"
}

export function PaymentDetailPageContent({ paymentId }: PaymentDetailPageContentProps) {
  const [payment, setPayment] = useState<PaymentSummary | null>(null)
  const [measurement, setMeasurement] = useState<MeasurementSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmittingAction, setIsSubmittingAction] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  // Nota Fiscal state
  const [nfFile, setNfFile] = useState<File | null>(null)
  const [nfNumero, setNfNumero] = useState("")
  const [nfDataEmissao, setNfDataEmissao] = useState("")
  const [nfValor, setNfValor] = useState("")
  const [isExtractingNF, setIsExtractingNF] = useState(false)
  const [nfExtractError, setNfExtractError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadPayment = async () => {
    try {
      setIsLoading(true)
      setLoadError(null)
      const data = await getPayment(Number(paymentId))
      setPayment(data)
      if (data.measurement) {
        try {
          const measurementData = await getMeasurement(data.measurement)
          setMeasurement(measurementData)
        } catch {
          // silently ignore
        }
      }
    } catch (paymentLoadError) {
      setLoadError(
        paymentLoadError instanceof Error
          ? paymentLoadError.message
          : "Não foi possível carregar o pagamento"
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadPayment()
  }, [paymentId])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setNfFile(file)
    setNfExtractError(null)
    // Extrai automaticamente ao selecionar arquivo
    setIsExtractingNF(true)
    try {
      const dados = await extractNfData(file)
      if (dados.numero_nota_fiscal) setNfNumero(dados.numero_nota_fiscal)
      if (dados.data_emissao_nota) setNfDataEmissao(dados.data_emissao_nota)
      if (dados.valor_nota_fiscal !== null && dados.valor_nota_fiscal !== undefined)
        setNfValor(String(dados.valor_nota_fiscal))
    } catch {
      setNfExtractError("Não foi possível extrair dados da NF via IA. Preencha manualmente.")
    } finally {
      setIsExtractingNF(false)
    }
  }

  const handleMarkAsPaid = async () => {
    if (!payment || payment.status !== "PENDING") return
    try {
      setIsSubmittingAction(true)
      setActionError(null)
      const formData = new FormData()
      if (nfNumero) formData.append("numero_nota_fiscal", nfNumero)
      if (nfDataEmissao) formData.append("data_emissao_nota", nfDataEmissao)
      if (nfValor) formData.append("valor_nota_fiscal", nfValor)
      if (nfFile) formData.append("anexo_nota_fiscal", nfFile)
      await markPaymentAsPaid(payment.id, formData)
      await loadPayment()
    } catch (paymentActionError) {
      setActionError(
        paymentActionError instanceof Error
          ? paymentActionError.message
          : "Não foi possível marcar o pagamento como pago"
      )
    } finally {
      setIsSubmittingAction(false)
    }
  }

  const handleMarkAsFailed = async () => {
    if (!payment || payment.status !== "PENDING") return
    try {
      setIsSubmittingAction(true)
      setActionError(null)
      await markPaymentAsFailed(payment.id)
      await loadPayment()
    } catch (paymentActionError) {
      setActionError(
        paymentActionError instanceof Error
          ? paymentActionError.message
          : "Não foi possível marcar o pagamento como falho"
      )
    } finally {
      setIsSubmittingAction(false)
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando pagamento...</p>
  }

  if (loadError) {
    return (
      <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
        <p className="text-sm font-medium text-destructive">Falha ao carregar pagamento</p>
        <p className="text-sm text-muted-foreground">{loadError}</p>
        <Link href="/payments" className={buttonVariants({ variant: "outline" })}>
          Voltar para pagamentos
        </Link>
      </div>
    )
  }

  if (!payment) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">Pagamento não encontrado.</p>
        <Link href="/payments" className={buttonVariants({ variant: "outline" })}>
          Voltar para pagamentos
        </Link>
      </div>
    )
  }

  const hasNf = payment.status === "PAID" && (
    payment.numero_nota_fiscal ||
    payment.data_emissao_nota ||
    payment.valor_nota_fiscal ||
    payment.anexo_nota_fiscal_url
  )

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Pagamento #{payment.id}</p>
            <h2 className="text-2xl font-semibold tracking-tight">
              {payment.contract_title ?? `Contrato #${payment.contract}`}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={payment.status === "PAID" ? "default" : "secondary"}>
              {formatPaymentStatusLabel(payment.status)}
            </Badge>
            <Link href="/payments" className={buttonVariants({ variant: "outline" })}>
              Voltar
            </Link>
          </div>
        </div>
      </section>

      {/* Informações de medição */}
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Informações de medição</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {measurement ? (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">Início</p>
                  <p className="text-sm font-medium">{formatDate(measurement.start_date)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Fim</p>
                  <p className="text-sm font-medium">{formatDate(measurement.end_date)}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Valor</p>
                <p className="text-sm font-medium">{formatMoney(measurement.value)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Descrição</p>
                <p className="text-sm">{measurement.description || "Sem descrição"}</p>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 border-t pt-4">
                <div>
                  <p className="text-xs text-muted-foreground">Criada em</p>
                  <p className="text-sm font-medium">{formatDate(measurement.created_at)}</p>
                </div>
                {measurement.status === "APPROVED" && (
                  <>
                    <div>
                      <p className="text-xs text-muted-foreground">Aprovada em</p>
                      <p className="text-sm font-medium">{formatDate(measurement.approved_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Aprovada por</p>
                      <p className="text-sm font-medium">{measurement.approved_by_name ?? "-"}</p>
                    </div>
                  </>
                )}
                {measurement.status === "REJECTED" && (
                  <>
                    <div>
                      <p className="text-xs text-muted-foreground">Rejeitada em</p>
                      <p className="text-sm font-medium">{formatDate(measurement.rejected_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Rejeitada por</p>
                      <p className="text-sm font-medium">{measurement.rejected_by_name ?? "-"}</p>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Medição não encontrada.</p>
          )}
        </CardContent>
      </Card>

      {/* Nota Fiscal — exibe quando PAID */}
      {hasNf ? (
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Nota Fiscal</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <p className="text-xs text-muted-foreground">Número da NF</p>
                <p className="text-sm font-medium">{payment.numero_nota_fiscal || "-"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Data de emissão</p>
                <p className="text-sm font-medium">{formatDate(payment.data_emissao_nota)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Valor da NF</p>
                <p className="text-sm font-medium">{payment.valor_nota_fiscal ? formatMoney(payment.valor_nota_fiscal) : "-"}</p>
              </div>
            </div>
            {payment.anexo_nota_fiscal_url ? (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Anexo</p>
                <a
                  href={payment.anexo_nota_fiscal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-primary underline underline-offset-2"
                >
                  Visualizar arquivo NF
                </a>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {/* Ações do pagamento */}
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Ações do pagamento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {payment.status === "PENDING" ? (
            <>
              {/* Upload da Nota Fiscal */}
              <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
                <p className="text-sm font-medium">Nota Fiscal (opcional)</p>
                <p className="text-xs text-muted-foreground">
                  Anexe a NF para que a IA preencha os campos automaticamente, ou preencha manualmente.
                </p>

                <div className="flex items-center gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,image/*"
                    className="hidden"
                    onChange={(e) => void handleFileChange(e)}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isExtractingNF}
                  >
                    {isExtractingNF ? "Extraindo via IA..." : "Anexar NF"}
                  </Button>
                  {nfFile ? (
                    <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                      {nfFile.name}
                    </span>
                  ) : null}
                </div>

                {nfExtractError ? (
                  <p className="text-xs text-amber-600">{nfExtractError}</p>
                ) : null}

                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">Número da NF</label>
                    <input
                      type="text"
                      className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                      placeholder="Ex: NF-0001"
                      value={nfNumero}
                      onChange={(e) => setNfNumero(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">Data de emissão</label>
                    <input
                      type="date"
                      className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                      value={nfDataEmissao}
                      onChange={(e) => setNfDataEmissao(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground">Valor da NF (R$)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
                      placeholder="0,00"
                      value={nfValor}
                      onChange={(e) => setNfValor(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={() => void handleMarkAsPaid()}
                  disabled={isSubmittingAction}
                >
                  {isSubmittingAction ? "Processando..." : "Marcar como pago"}
                </Button>
                <Button
                  variant="outline"
                  className="border-destructive/40 text-destructive hover:bg-destructive/10"
                  onClick={() => void handleMarkAsFailed()}
                  disabled={isSubmittingAction}
                >
                  {isSubmittingAction ? "Processando..." : "Marcar como falho"}
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Este pagamento já está {formatPaymentStatusLabel(payment.status)}.
            </p>
          )}

          {actionError ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {actionError}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
