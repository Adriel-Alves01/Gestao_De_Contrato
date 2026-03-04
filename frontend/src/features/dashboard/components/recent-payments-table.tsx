"use client"

import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { listPaymentsPaginated } from "@/services/api/payments"
import { ApiRequestError } from "@/services/api/client"
import type { PaymentSummary } from "@/types/payments"

function formatMoney(value: string) {
  const parsedValue = Number(value)
  if (Number.isNaN(parsedValue)) {
    return value
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(parsedValue)
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date)
}

function getStatusLabel(status: PaymentSummary["status"]) {
  switch (status) {
    case "PENDING":
      return "Pendente"
    case "PAID":
      return "Pago"
    case "FAILED":
      return "Falhou"
    default:
      return status
  }
}

function getStatusVariant(status: PaymentSummary["status"]) {
  if (status === "PAID") {
    return "default" as const
  }

  if (status === "FAILED") {
    return "outline" as const
  }

  return "secondary" as const
}

function getStatusClassName(status: PaymentSummary["status"]) {
  if (status === "FAILED") {
    return "border-destructive/40 bg-destructive/10 text-destructive"
  }

  return undefined
}

export function RecentPaymentsTable() {
  const [payments, setPayments] = useState<PaymentSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPayments = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const data = await listPaymentsPaginated(1)
        setPayments(data.results.slice(0, 6))
      } catch (loadError) {
        const message =
          loadError instanceof ApiRequestError || loadError instanceof Error
            ? loadError.message
            : "Não foi possível carregar pagamentos"

        setError(message)
      } finally {
        setIsLoading(false)
      }
    }

    void loadPayments()
  }, [])

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Pagamentos recentes</CardTitle>
        <Badge variant="outline">Endpoint /api/v1/payments/</Badge>
      </CardHeader>
      <CardContent>
        {isLoading ? <p className="text-sm text-muted-foreground">Carregando pagamentos...</p> : null}

        {!isLoading && error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3">
            <p className="text-sm font-medium text-destructive">Falha ao carregar pagamentos</p>
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        ) : null}

        {!isLoading && !error && payments.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum pagamento encontrado.</p>
        ) : null}

        {!isLoading && !error && payments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-3 font-medium">Pagamento</th>
                  <th className="pb-3 font-medium">Contrato</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Criado em</th>
                  <th className="pb-3 text-right font-medium">Valor</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id} className="border-b transition-colors hover:bg-muted/50 last:border-0">
                    <td className="py-3 font-medium">#{payment.id}</td>
                    <td className="py-3">#{payment.contract}</td>
                    <td className="py-3">
                      <Badge
                        variant={getStatusVariant(payment.status)}
                        className={getStatusClassName(payment.status)}
                      >
                        {getStatusLabel(payment.status)}
                      </Badge>
                    </td>
                    <td className="py-3">{formatDate(payment.created_at)}</td>
                    <td className="py-3 text-right">{formatMoney(payment.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
