"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  getPayment,
  markPaymentAsFailed,
  markPaymentAsPaid,
} from "@/services/api/payments"
import type { PaymentSummary } from "@/types/payments"

interface PaymentDetailPageContentProps {
  paymentId: string
}

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

function formatDate(value: string | null) {
  if (!value) {
    return "-"
  }

  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("pt-BR").format(parsedDate)
}

function formatPaymentStatusLabel(status: PaymentSummary["status"]) {
  if (status === "PAID") {
    return "pago"
  }

  if (status === "FAILED") {
    return "falhou"
  }

  return "pendente"
}

export function PaymentDetailPageContent({ paymentId }: PaymentDetailPageContentProps) {
  const [payment, setPayment] = useState<PaymentSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmittingAction, setIsSubmittingAction] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadPayment = async () => {
    try {
      setIsLoading(true)
      setLoadError(null)

      const data = await getPayment(Number(paymentId))
      setPayment(data)
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

  const handleMarkAsPaid = async () => {
    if (!payment || payment.status !== "PENDING") {
      return
    }

    try {
      setIsSubmittingAction(true)
      setActionError(null)
      await markPaymentAsPaid(payment.id)
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
    if (!payment || payment.status !== "PENDING") {
      return
    }

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

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Pagamento #{payment.id}</p>
            <h2 className="text-2xl font-semibold tracking-tight">Medição #{payment.measurement}</h2>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={payment.status === "PAID" ? "default" : "secondary"}>
              {payment.status}
            </Badge>
            <Link href="/payments" className={buttonVariants({ variant: "outline" })}>
              Voltar
            </Link>
          </div>
        </div>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Informações do pagamento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Contrato</p>
              <p className="text-sm font-medium">#{payment.contract}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Medição</p>
              <p className="text-sm font-medium">#{payment.measurement}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Valor</p>
              <p className="text-sm font-medium">{formatMoney(payment.amount)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Criado em</p>
              <p className="text-sm font-medium">{formatDate(payment.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Pago em</p>
              <p className="text-sm font-medium">{formatDate(payment.paid_at)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Ações do pagamento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Button
              onClick={() => void handleMarkAsPaid()}
              disabled={isSubmittingAction || payment.status !== "PENDING"}
            >
              {isSubmittingAction ? "Processando..." : "Marcar como pago"}
            </Button>
            <Button
              variant="outline"
              className="border-destructive/40 text-destructive hover:bg-destructive/10"
              onClick={() => void handleMarkAsFailed()}
              disabled={isSubmittingAction || payment.status !== "PENDING"}
            >
              {isSubmittingAction ? "Processando..." : "Marcar como falho"}
            </Button>
          </div>

          {actionError ? (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {actionError}
            </div>
          ) : null}

          {payment.status !== "PENDING" ? (
            <p className="text-sm text-muted-foreground">
              Este pagamento já está {formatPaymentStatusLabel(payment.status)}.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
