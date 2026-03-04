"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCurrentUser } from "@/hooks/use-current-user"
import { listContractsPaginated } from "@/services/api/contracts"
import { listMeasurementsPaginated } from "@/services/api/measurements"
import type { MeasurementSummary } from "@/types/measurements"

const GESTOR_PAGE_SIZE = 15

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

function formatMeasurementStatusLabel(status: MeasurementSummary["status"]) {
  if (status === "APPROVED") {
    return "Aprovada"
  }

  if (status === "REJECTED") {
    return "Rejeitada"
  }

  return "Pendente"
}

export function MeasurementsPageContent() {
  const router = useRouter()
  const { user, isLoadingUser, isFinancialUser } = useCurrentUser()
  const [measurements, setMeasurements] = useState<MeasurementSummary[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalMeasurements, setTotalMeasurements] = useState(0)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [hasPreviousPage, setHasPreviousPage] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isGestorUser = user?.groups.includes("GESTOR") ?? false

  const loadGestorMeasurements = async (page = 1) => {
    if (!user) {
      setMeasurements([])
      setTotalMeasurements(0)
      setHasNextPage(false)
      setHasPreviousPage(false)
      setCurrentPage(1)
      return
    }

    const ownContracts: number[] = []
    let contractsPage = 1

    while (true) {
      const contractsResponse = await listContractsPaginated(contractsPage, {
        managerId: user.id,
        pageSize: 100,
      })

      ownContracts.push(...contractsResponse.results.map((contract) => contract.id))

      if (!contractsResponse.next) {
        break
      }

      contractsPage += 1
    }

    if (ownContracts.length === 0) {
      setMeasurements([])
      setTotalMeasurements(0)
      setHasNextPage(false)
      setHasPreviousPage(false)
      setCurrentPage(1)
      return
    }

    const allMeasurements: MeasurementSummary[] = []

    for (const contractId of ownContracts) {
      let measurementPage = 1

      while (true) {
        const measurementsResponse = await listMeasurementsPaginated(
          measurementPage,
          {
            contractId,
            pageSize: 100,
          }
        )

        allMeasurements.push(...measurementsResponse.results)

        if (!measurementsResponse.next) {
          break
        }

        measurementPage += 1
      }
    }

    allMeasurements.sort(
      (firstItem, secondItem) =>
        new Date(secondItem.created_at).getTime()
        - new Date(firstItem.created_at).getTime()
    )

    const startIndex = (page - 1) * GESTOR_PAGE_SIZE
    const endIndex = startIndex + GESTOR_PAGE_SIZE

    setMeasurements(allMeasurements.slice(startIndex, endIndex))
    setTotalMeasurements(allMeasurements.length)
    setHasNextPage(endIndex < allMeasurements.length)
    setHasPreviousPage(page > 1)
    setCurrentPage(page)
  }

  const loadMeasurements = async (page = 1) => {
    if (isGestorUser && !user) {
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      if (isGestorUser) {
        await loadGestorMeasurements(page)
        return
      }

      const data = await listMeasurementsPaginated(page)
      setMeasurements(data.results)
      setTotalMeasurements(data.count)
      setHasNextPage(Boolean(data.next))
      setHasPreviousPage(Boolean(data.previous))
      setCurrentPage(page)
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Não foi possível carregar medições"
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isLoadingUser) {
      return
    }

    void loadMeasurements(1)
  }, [isLoadingUser, user?.id])

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">Medições</h2>

          <div className="flex items-center gap-2">
            {!isFinancialUser ? (
              <Link href="/measurements/new" className={buttonVariants()}>
                Nova medição
              </Link>
            ) : null}
            <Button variant="outline" onClick={() => void loadMeasurements(currentPage)}>
              Atualizar
            </Button>
          </div>
        </div>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Lista de medições</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Carregando medições...</p>
          ) : null}

          {!isLoading && error ? (
            <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
              <p className="text-sm font-medium text-destructive">Falha ao carregar medições</p>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button size="sm" variant="outline" onClick={() => void loadMeasurements(currentPage)}>
                Tentar novamente
              </Button>
            </div>
          ) : null}

          {!isLoading && !error && measurements.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhuma medição encontrada.</p>
          ) : null}

          {!isLoading && !error && measurements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">ID</th>
                    <th className="pb-3 font-medium">Contrato</th>
                    <th className="pb-3 font-medium">Descrição</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Criada em</th>
                    <th className="pb-3 text-right font-medium">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements.map((measurement) => (
                    <tr
                      key={measurement.id}
                      className="cursor-pointer border-b transition-colors hover:bg-muted/50 last:border-0"
                      onClick={() => router.push(`/measurements/${measurement.id}`)}
                    >
                      <td className="py-3 font-medium">#{measurement.id}</td>
                      <td className="py-3">#{measurement.contract}</td>
                      <td className="py-3">{measurement.description || "Sem descrição"}</td>
                      <td className="py-3">
                        <Badge
                          variant={measurement.status === "APPROVED" ? "default" : "secondary"}
                        >
                          {formatMeasurementStatusLabel(measurement.status)}
                        </Badge>
                      </td>
                      <td className="py-3">{formatDate(measurement.created_at)}</td>
                      <td className="py-3 text-right">{formatMoney(measurement.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {!isLoading && !error && measurements.length > 0 ? (
            <div className="mt-4 flex items-center justify-between gap-3 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Página {currentPage} • {totalMeasurements} medição(ões)
              </p>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadMeasurements(currentPage - 1)}
                  disabled={!hasPreviousPage || isLoading}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadMeasurements(currentPage + 1)}
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
