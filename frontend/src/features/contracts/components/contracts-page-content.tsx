"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCurrentUser } from "@/hooks/use-current-user"
import { listContractsPaginated } from "@/services/api/contracts"
import type { ContractSummary } from "@/types/contracts"

function getManagerName(contract: ContractSummary) {
  if (!contract.manager) {
    return "Sem gestor"
  }

  const fullName = `${contract.manager.first_name} ${contract.manager.last_name}`.trim()
  return fullName || contract.manager.username
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

function formatContractStatusLabel(status: ContractSummary["status"]) {
  if (status === "ACTIVE") {
    return "Ativo"
  }

  if (status === "CLOSED") {
    return "Fechado"
  }

  return status
}

export function ContractsPageContent() {
  const router = useRouter()
  const { user, isLoadingUser, isFinancialUser } = useCurrentUser()
  const [contracts, setContracts] = useState<ContractSummary[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalContracts, setTotalContracts] = useState(0)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [hasPreviousPage, setHasPreviousPage] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isGestorUser = user?.groups.includes("GESTOR") ?? false

  const loadContracts = async (page = 1) => {
    if (isGestorUser && !user) {
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const data = await listContractsPaginated(
        page,
        isGestorUser && user
          ? { managerId: user.id }
          : undefined
      )
      setContracts(data.results)
      setTotalContracts(data.count)
      setHasNextPage(Boolean(data.next))
      setHasPreviousPage(Boolean(data.previous))
      setCurrentPage(page)
    } catch (loadError) {
      const message =
        loadError instanceof Error
          ? loadError.message
          : "Não foi possível carregar contratos"
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isLoadingUser) {
      return
    }

    void loadContracts(1)
  }, [isLoadingUser, user?.id])

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Contratos</h2>
          </div>

          <div className="flex items-center gap-2">
            {!isFinancialUser ? (
              <Link href="/contracts/new" className={buttonVariants()}>
                Novo contrato
              </Link>
            ) : null}
            <Button variant="outline" onClick={() => void loadContracts()}>
              Atualizar
            </Button>
          </div>
        </div>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Lista de contratos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Carregando contratos...</p>
          ) : null}

          {!isLoading && error ? (
            <div className="space-y-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
              <p className="text-sm font-medium text-destructive">Falha ao carregar contratos</p>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button size="sm" variant="outline" onClick={() => void loadContracts()}>
                Tentar novamente
              </Button>
            </div>
          ) : null}

          {!isLoading && !error && contracts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum contrato encontrado.</p>
          ) : null}

          {!isLoading && !error && contracts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 font-medium">Título</th>
                    <th className="pb-3 font-medium">Gestor</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Vigência</th>
                    <th className="pb-3 text-right font-medium">Saldo</th>
                    <th className="pb-3 text-right font-medium">Valor total</th>
                  </tr>
                </thead>
                <tbody>
                  {contracts.map((contract) => (
                    <tr
                      key={contract.id}
                      className="cursor-pointer border-b transition-colors hover:bg-muted/50 last:border-0"
                      onClick={() => router.push(`/contracts/${contract.id}`)}
                    >
                      <td className="py-3 font-medium">{contract.title}</td>
                      <td className="py-3">{getManagerName(contract)}</td>
                      <td className="py-3">
                        <Badge variant={contract.status === "ACTIVE" ? "default" : "secondary"}>
                            {formatContractStatusLabel(contract.status)}
                        </Badge>
                      </td>
                      <td className="py-3">
                        {formatDate(contract.start_date)} até {formatDate(contract.end_date)}
                      </td>
                      <td className="py-3 text-right">{formatMoney(contract.remaining_balance)}</td>
                      <td className="py-3 text-right">{formatMoney(contract.total_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {!isLoading && !error && contracts.length > 0 ? (
            <div className="mt-4 flex items-center justify-between gap-3 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Página {currentPage} • {totalContracts} contrato(s)
              </p>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadContracts(currentPage - 1)}
                  disabled={!hasPreviousPage || isLoading}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadContracts(currentPage + 1)}
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
