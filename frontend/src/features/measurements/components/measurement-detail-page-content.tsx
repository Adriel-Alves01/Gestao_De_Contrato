"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCurrentUser } from "@/hooks/use-current-user"
import {
  approveMeasurement,
  deleteMeasurement,
  getMeasurement,
  rejectMeasurement,
} from "@/services/api/measurements"
import type { MeasurementSummary } from "@/types/measurements"

interface MeasurementDetailPageContentProps {
  measurementId: string
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

function formatMeasurementStatusLabel(status: MeasurementSummary["status"]) {
  if (status === "APPROVED") {
    return "aprovada"
  }

  if (status === "REJECTED") {
    return "rejeitada"
  }

  return "pendente"
}

export function MeasurementDetailPageContent({ measurementId }: MeasurementDetailPageContentProps) {
  const router = useRouter()
  const { isFinancialUser } = useCurrentUser()
  const [measurement, setMeasurement] = useState<MeasurementSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmittingAction, setIsSubmittingAction] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadMeasurement = async () => {
    try {
      setIsLoading(true)
      setLoadError(null)

      const data = await getMeasurement(Number(measurementId))
      setMeasurement(data)
    } catch (measurementLoadError) {
      setLoadError(
        measurementLoadError instanceof Error
          ? measurementLoadError.message
          : "Não foi possível carregar a medição"
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadMeasurement()
  }, [measurementId])

  const handleApproveMeasurement = async () => {
    if (!measurement || measurement.status !== "PENDING") {
      return
    }

    try {
      setIsSubmittingAction(true)
      setActionError(null)
      await approveMeasurement(measurement.id)
      await loadMeasurement()
    } catch (measurementActionError) {
      setActionError(
        measurementActionError instanceof Error
          ? measurementActionError.message
          : "Não foi possível aprovar a medição"
      )
    } finally {
      setIsSubmittingAction(false)
    }
  }

  const handleRejectMeasurement = async () => {
    if (!measurement || measurement.status !== "PENDING") {
      return
    }

    try {
      setIsSubmittingAction(true)
      setActionError(null)
      await rejectMeasurement(measurement.id)
      await loadMeasurement()
    } catch (measurementActionError) {
      setActionError(
        measurementActionError instanceof Error
          ? measurementActionError.message
          : "Não foi possível rejeitar a medição"
      )
    } finally {
      setIsSubmittingAction(false)
    }
  }

  const handleDeleteMeasurement = async () => {
    if (!measurement || measurement.status !== "PENDING") {
      return
    }

    try {
      setIsDeleting(true)
      setActionError(null)
      await deleteMeasurement(measurement.id)
      router.push("/measurements")
    } catch (measurementActionError) {
      setActionError(
        measurementActionError instanceof Error
          ? measurementActionError.message
          : "Não foi possível excluir a medição"
      )
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando medição...</p>
  }

  if (loadError) {
    return (
      <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
        <p className="text-sm font-medium text-destructive">Falha ao carregar medição</p>
        <p className="text-sm text-muted-foreground">{loadError}</p>
        <Link href="/measurements" className={buttonVariants({ variant: "outline" })}>
          Voltar para medições
        </Link>
      </div>
    )
  }

  if (!measurement) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">Medição não encontrada.</p>
        <Link href="/measurements" className={buttonVariants({ variant: "outline" })}>
          Voltar para medições
        </Link>
      </div>
    )
  }

  const canEditMeasurement = measurement.status === "PENDING" && !isFinancialUser

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Medição #{measurement.id}</p>
            <h2 className="text-2xl font-semibold tracking-tight">Contrato #{measurement.contract}</h2>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={measurement.status === "APPROVED" ? "default" : "secondary"}>
              {measurement.status}
            </Badge>
            {canEditMeasurement ? (
              <>
                <Link href={`/measurements/${measurement.id}/edit`} className={buttonVariants()}>
                  Editar
                </Link>
                <Button
                  variant="outline"
                  className="border-destructive/40 text-destructive hover:bg-destructive/10"
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={isDeleting}
                >
                  {isDeleting ? "Excluindo..." : "Excluir"}
                </Button>
              </>
            ) : null}
            <Link href="/measurements" className={buttonVariants({ variant: "outline" })}>
              Voltar
            </Link>
          </div>
        </div>

        {showDeleteConfirm ? (
          <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4">
            <p className="text-sm font-medium text-destructive">
              Deseja excluir esta medição?
            </p>
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
              >
                Cancelar
              </Button>
              <Button
                variant="outline"
                className="border-destructive/40 text-destructive hover:bg-destructive/10"
                onClick={() => void handleDeleteMeasurement()}
                disabled={isDeleting}
              >
                {isDeleting ? "Excluindo..." : "Confirmar"}
              </Button>
            </div>
          </div>
        ) : null}
      </section>

      {!canEditMeasurement ? (
        <div className="rounded-lg border border-muted bg-muted/40 p-3 text-sm text-muted-foreground">
          Esta medição está {measurement.status} e não pode mais ser editada.
        </div>
      ) : null}

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Informações da medição</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Valor</p>
              <p className="text-sm font-medium">{formatMoney(measurement.value)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Criada em</p>
              <p className="text-sm font-medium">{formatDate(measurement.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Aprovada em</p>
              <p className="text-sm font-medium">{formatDate(measurement.approved_at)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Rejeitada em</p>
              <p className="text-sm font-medium">{formatDate(measurement.rejected_at)}</p>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground">Descrição</p>
            <p className="text-sm">{measurement.description || "Sem descrição"}</p>
          </div>
        </CardContent>
      </Card>

      {!isFinancialUser ? (
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Ações da medição</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <Button
                onClick={() => void handleApproveMeasurement()}
                disabled={isSubmittingAction || measurement.status !== "PENDING"}
              >
                {isSubmittingAction ? "Processando..." : "Aprovar medição"}
              </Button>
              <Button
                variant="outline"
                className="border-destructive/40 text-destructive hover:bg-destructive/10"
                onClick={() => void handleRejectMeasurement()}
                disabled={isSubmittingAction || measurement.status !== "PENDING"}
              >
                {isSubmittingAction ? "Processando..." : "Rejeitar medição"}
              </Button>
            </div>

            {actionError ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {actionError}
              </div>
            ) : null}

            {measurement.status !== "PENDING" ? (
              <p className="text-sm text-muted-foreground">
                A medição já está {formatMeasurementStatusLabel(measurement.status)}.
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
