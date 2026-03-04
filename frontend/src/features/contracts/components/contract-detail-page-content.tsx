"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCurrentUser } from "@/hooks/use-current-user"
import { closeContract, deleteContract, getContract } from "@/services/api/contracts"
import { listMeasurementsByContract } from "@/services/api/measurements"
import { listPaymentsByContract } from "@/services/api/payments"
import type { ContractSummary } from "@/types/contracts"
import type { MeasurementSummary } from "@/types/measurements"
import type { PaymentSummary } from "@/types/payments"

interface ContractDetailPageContentProps {
  contractId: string
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

function formatDate(value: string) {
  const parsedDate = new Date(value)
  if (Number.isNaN(parsedDate.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("pt-BR").format(parsedDate)
}

function getManagerName(contract: ContractSummary) {
  if (!contract.manager) {
    return "Sem gestor"
  }

  const fullName = `${contract.manager.first_name} ${contract.manager.last_name}`.trim()
  return fullName || contract.manager.username
}

function getPaymentStatusInfo(
  measurement: MeasurementSummary,
  paymentsByMeasurementId: Record<number, PaymentSummary>
) {
  const payment = paymentsByMeasurementId[measurement.id]

  if (!payment) {
    return {
      label: "-",
      variant: "outline" as const,
      className: "",
    }
  }

  if (payment.status === "PAID") {
    return {
      label: "Pago",
      variant: "default" as const,
      className: "",
    }
  }

  if (payment.status === "FAILED") {
    return {
      label: "Falha",
      variant: "outline" as const,
      className: "border-destructive/40 text-destructive",
    }
  }

  return {
    label: "Pendente",
    variant: "secondary" as const,
    className: "",
  }
}

export function ContractDetailPageContent({ contractId }: ContractDetailPageContentProps) {
  const router = useRouter()
  const { isFinancialUser } = useCurrentUser()
  const [contract, setContract] = useState<ContractSummary | null>(null)
  const [measurements, setMeasurements] = useState<MeasurementSummary[]>([])
  const [paymentsByMeasurementId, setPaymentsByMeasurementId] = useState<
    Record<number, PaymentSummary>
  >({})
  const [isLoadingMeasurements, setIsLoadingMeasurements] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isClosing, setIsClosing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDeleteContract = async () => {
    try {
      setIsDeleting(true)
      await deleteContract(Number(contractId))
      router.push("/contracts")
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Não foi possível excluir o contrato"
      )
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const handleCloseContract = async () => {
    try {
      setIsClosing(true)
      setError(null)

      const updatedContract = await closeContract(Number(contractId))
      setContract(updatedContract)
    } catch (closeError) {
      setError(
        closeError instanceof Error
          ? closeError.message
          : "Não foi possível fechar o contrato"
      )
    } finally {
      setIsClosing(false)
    }
  }

  useEffect(() => {
    const loadContract = async () => {
      try {
        setIsLoading(true)
        setIsLoadingMeasurements(true)
        setError(null)

        const parsedId = Number(contractId)
        const [contractData, measurementsData, paymentsData] = await Promise.all([
          getContract(parsedId),
          listMeasurementsByContract(parsedId),
          listPaymentsByContract(parsedId),
        ])

        const paymentsMap = paymentsData.reduce<Record<number, PaymentSummary>>(
          (accumulator, payment) => {
            accumulator[payment.measurement] = payment
            return accumulator
          },
          {}
        )

        setContract(contractData)
        setMeasurements(measurementsData)
        setPaymentsByMeasurementId(paymentsMap)
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Não foi possível carregar o contrato"
        )
      } finally {
        setIsLoading(false)
        setIsLoadingMeasurements(false)
      }
    }

    void loadContract()
  }, [contractId])

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando informações do contrato...</p>
  }

  if (error) {
    return (
      <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
        <p className="text-sm font-medium text-destructive">Falha ao carregar contrato</p>
        <p className="text-sm text-muted-foreground">{error}</p>
        <Link href="/contracts" className={buttonVariants({ variant: "outline" })}>
          Voltar para contratos
        </Link>
      </div>
    )
  }

  if (!contract) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">Contrato não encontrado.</p>
        <Link href="/contracts" className={buttonVariants({ variant: "outline" })}>
          Voltar para contratos
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Contrato #{contract.id}</p>
            <h2 className="text-2xl font-semibold tracking-tight">{contract.title}</h2>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={contract.status === "ACTIVE" ? "default" : "secondary"}>
              {contract.status}
            </Badge>
            {!isFinancialUser ? (
              <>
                <Link href={`/contracts/${contract.id}/edit`} className={buttonVariants()}>
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
            <Link href="/contracts" className={buttonVariants({ variant: "outline" })}>
              Voltar
            </Link>
          </div>
        </div>

        {!isFinancialUser && showDeleteConfirm ? (
          <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-4">
            <p className="text-sm font-medium text-destructive">
              Deseja excluir este contrato?
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
                onClick={() => void handleDeleteContract()}
                disabled={isDeleting}
              >
                {isDeleting ? "Excluindo..." : "Confirmar"}
              </Button>
            </div>
          </div>
        ) : null}
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Informações do contrato</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Gestor</p>
              <p className="text-sm font-medium">{getManagerName(contract)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Vigência</p>
              <p className="text-sm font-medium">
                {formatDate(contract.start_date)} até {formatDate(contract.end_date)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Valor total</p>
              <p className="text-sm font-medium">{formatMoney(contract.total_value)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Saldo restante</p>
              <p className="text-sm font-medium">{formatMoney(contract.remaining_balance)}</p>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground">Descrição</p>
            <p className="text-sm">{contract.description || "Sem descrição"}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Medições do contrato</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingMeasurements ? (
            <p className="text-sm text-muted-foreground">Carregando medições do contrato...</p>
          ) : null}

          {!isLoadingMeasurements && measurements.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nenhuma medição criada para este contrato.
            </p>
          ) : null}

          {!isLoadingMeasurements && measurements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">ID</th>
                    <th className="pb-3 font-medium">Descrição</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Status do pagamento</th>
                    <th className="pb-3 font-medium">Criada em</th>
                    <th className="pb-3 text-right font-medium">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements.map((measurement) => {
                    const paymentStatus = getPaymentStatusInfo(
                      measurement,
                      paymentsByMeasurementId
                    )

                    return (
                      <tr
                        key={measurement.id}
                        className="cursor-pointer border-b transition-colors hover:bg-muted/50 last:border-0"
                        onClick={() => router.push(`/measurements/${measurement.id}`)}
                      >
                        <td className="py-3">
                          <Link
                            href={`/measurements/${measurement.id}`}
                            className="font-medium hover:underline"
                          >
                            #{measurement.id}
                          </Link>
                        </td>
                        <td className="py-3">{measurement.description || "Sem descrição"}</td>
                        <td className="py-3">
                          <Badge
                            variant={measurement.status === "APPROVED" ? "default" : "secondary"}
                          >
                            {measurement.status}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <Badge variant={paymentStatus.variant} className={paymentStatus.className}>
                            {paymentStatus.label}
                          </Badge>
                        </td>
                        <td className="py-3">{formatDate(measurement.created_at)}</td>
                        <td className="py-3 text-right">{formatMoney(measurement.value)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {!isFinancialUser ? (
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Fechar contrato</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Encerrar este contrato para impedir novas movimentações operacionais.
            </p>

            <Button
              variant="outline"
              className="border-destructive/40 text-destructive hover:bg-destructive/10"
              onClick={() => void handleCloseContract()}
              disabled={isClosing || contract.status === "CLOSED"}
            >
              {contract.status === "CLOSED"
                ? "Contrato já fechado"
                : isClosing
                  ? "Fechando..."
                  : "Fechar contrato"}
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
