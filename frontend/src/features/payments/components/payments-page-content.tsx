"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { listPaymentsPaginated } from "@/services/api/payments"
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
  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("pt-BR").format(parsedDate)
}

function formatPaymentStatusLabel(status: PaymentSummary["status"]) {
  if (status === "PAID") {
    return "Pago"
  }

  if (status === "FAILED") {
    return "Falhou"
  }

  return "Pendente"
}

export function PaymentsPageContent() {
  const router = useRouter()
  const [payments, setPayments] = useState<PaymentSummary[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPayments, setTotalPayments] = useState(0)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [hasPreviousPage, setHasPreviousPage] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPayments = async (page = 1) => {
    try {
      setIsLoading(true)
      setError(null)

      const data = await listPaymentsPaginated(page)
      setPayments(data.results)
      setTotalPayments(data.count)
      setHasNextPage(Boolean(data.next))
      setHasPreviousPage(Boolean(data.previous))
      setCurrentPage(page)
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Não foi possível carregar pagamentos"
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadPayments(1)
  }, [])

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">Pagamentos</h2>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => void loadPayments(currentPage)}>
              Atualizar
            </Button>
          </div>
        </div>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Lista de pagamentos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Carregando pagamentos...</p>
          ) : null}

          {!isLoading && error ? (
            <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
              <p className="text-sm font-medium text-destructive">Falha ao carregar pagamentos</p>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button size="sm" variant="outline" onClick={() => void loadPayments(currentPage)}>
                Tentar novamente
              </Button>
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
                    <th className="pb-3 font-medium">ID</th>
                    <th className="pb-3 font-medium">Contrato</th>
                    <th className="pb-3 font-medium">Medição</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Criado em</th>
                    <th className="pb-3 text-right font-medium">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((payment) => (
                    <tr
                      key={payment.id}
                      className="cursor-pointer border-b transition-colors hover:bg-muted/50 last:border-0"
                      onClick={() => router.push(`/payments/${payment.id}`)}
                    >
                      <td className="py-3 font-medium">#{payment.id}</td>
                      <td className="py-3">#{payment.contract}</td>
                      <td className="py-3">#{payment.measurement}</td>
                      <td className="py-3">
                        <Badge
                          variant={payment.status === "PAID" ? "default" : "secondary"}
                        >
                            {formatPaymentStatusLabel(payment.status)}
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

          {!isLoading && !error && payments.length > 0 ? (
            <div className="mt-4 flex items-center justify-between gap-3 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Página {currentPage} • {totalPayments} pagamento(s)
              </p>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadPayments(currentPage - 1)}
                  disabled={!hasPreviousPage || isLoading}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadPayments(currentPage + 1)}
                  disabled={!hasNextPage || isLoading}
                >
                  Próxima
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
