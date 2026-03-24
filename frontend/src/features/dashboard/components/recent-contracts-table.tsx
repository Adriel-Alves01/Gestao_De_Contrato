"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { env } from "@/config/env"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCurrentUser } from "@/hooks/use-current-user"
import { listContractsPaginated } from "@/services/api/contracts"
import { ApiRequestError } from "@/services/api/client"
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

function formatMonthYear(value: string) {
  const [year, month] = value.split("-")
  return `${month}/${year}`
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

export function RecentContractsTable() {
  const router = useRouter()
  const { user, isLoadingUser } = useCurrentUser()
  const [contracts, setContracts] = useState<ContractSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isUnauthorized, setIsUnauthorized] = useState(false)

  const isGestorUser = user?.groups.includes("GESTOR") ?? false

  useEffect(() => {
    if (isLoadingUser) {
      return
    }

    const loadContracts = async () => {
      try {
        setIsLoading(true)
        setError(null)
        setIsUnauthorized(false)

        const data = await listContractsPaginated(
          1,
          isGestorUser && user
            ? { pageSize: 10, managerId: user.id }
            : { pageSize: 10 }
        )

        const scopedResults =
          isGestorUser && user
            ? data.results.filter((contract) => contract.manager?.id === user.id)
            : data.results

        setContracts(scopedResults.slice(0, 10))
      } catch (loadError) {
        if (loadError instanceof ApiRequestError && loadError.status === 401) {
          setIsUnauthorized(true)
          setError("Você precisa estar autenticado para listar contratos.")
          return
        }

        const message =
          loadError instanceof Error
            ? loadError.message
            : "Não foi possível carregar contratos"

        setError(message)
      } finally {
        setIsLoading(false)
      }
    }

    void loadContracts()
  }, [isLoadingUser, isGestorUser, user?.id])

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>Contratos recentes</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Carregando contratos...</p>
        ) : null}

        {!isLoading && error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3">
            <p className="text-sm font-medium text-destructive">Falha ao carregar contratos</p>
            <p className="text-sm text-muted-foreground">{error}</p>

            {isUnauthorized ? (
              <div className="mt-3">
                <a href={`${env.apiBaseUrl}/api-auth/login/?next=/api/docs/`} target="_blank" rel="noreferrer">
                  <Button size="sm" variant="outline">Fazer login no backend</Button>
                </a>
              </div>
            ) : null}
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
              </tr>
            </thead>
            <tbody>
              {contracts.map((contract) => (
                <tr key={contract.id} className="cursor-pointer border-b transition-colors hover:bg-muted/50 last:border-0" onClick={() => router.push(`/contracts/${contract.id}`)}>
                  <td className="py-3 font-medium">{contract.title.length > 40 ? `${contract.title.slice(0, 40)}...` : contract.title}</td>
                  <td className="py-3">{getManagerName(contract)}</td>
                  <td className="py-3">
                    <Badge variant={contract.status === "ACTIVE" ? "default" : "secondary"}>
                      {formatContractStatusLabel(contract.status)}
                    </Badge>
                  </td>
                  <td className="py-3">
                    {formatMonthYear(contract.start_date)} até {formatMonthYear(contract.end_date)}
                  </td>
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
