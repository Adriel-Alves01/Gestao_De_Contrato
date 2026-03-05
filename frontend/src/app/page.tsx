"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"

import { AppShell } from "@/components/layout/app-shell"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { OverviewCards } from "@/features/dashboard/components/overview-cards"
import { RecentContractsTable } from "@/features/dashboard/components/recent-contracts-table"
import { RecentPaymentsTable } from "@/features/dashboard/components/recent-payments-table"
import { clearTokens, getCurrentUser } from "@/services/api/auth"
import { getAnalyticsOverview, type AnalyticsOverviewResponse } from "@/services/api/analytics"

function formatMoney(value: string) {
  const parsedValue = Number(value)
  if (Number.isNaN(parsedValue)) {
    return value
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(parsedValue)
}

function DashboardCardsSkeleton() {
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index} className="shadow-sm">
          <CardContent className="space-y-3 py-6">
            <div className="h-4 w-28 animate-pulse rounded bg-muted" />
            <div className="h-8 w-20 animate-pulse rounded bg-muted" />
            <div className="h-4 w-44 animate-pulse rounded bg-muted" />
          </CardContent>
        </Card>
      ))}
    </section>
  )
}

export default function Home() {
  const router = useRouter()
  const [isFinancialUser, setIsFinancialUser] = useState(false)
  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null)
  const [isDashboardContextLoading, setIsDashboardContextLoading] = useState(true)

  useEffect(() => {
    const loadDashboardContext = async () => {
      try {
        const [user, overviewData] = await Promise.all([
          getCurrentUser(),
          getAnalyticsOverview(),
        ])

        const isFinancial = user.groups.includes("FINANCEIRO")
        setIsFinancialUser(isFinancial)
        setOverview(overviewData)
      } catch {
        clearTokens()
        setIsFinancialUser(false)
        setOverview(null)
        router.replace("/login")
      } finally {
        setIsDashboardContextLoading(false)
      }
    }

    void loadDashboardContext()
  }, [router])

  const cards = useMemo(() => {
    if (!overview) {
      return undefined
    }

    if (!isFinancialUser) {
      return [
        {
          title: "Contratos Ativos",
          value: String(overview.contracts.active_contracts),
          description: `${overview.contracts.total_contracts} contrato(s) visível(is) para você`,
        },
        {
          title: "Medições Pendentes",
          value: String(overview.measurements.pending_measurements),
          description: `${formatMoney(overview.measurements.pending_value)} aguardando aprovação`,
        },
        {
          title: "Pagamentos Pendentes",
          value: String(overview.payments.pending_payments),
          description: `${formatMoney(overview.payments.pending_amount)} aguardando baixa`,
        },
      ]
    }

    return [
      {
        title: "Pagamentos Pendentes",
        value: String(overview.payments.pending_payments),
        description: `${formatMoney(overview.payments.pending_amount)} aguardando processamento`,
      },
      {
        title: "Pagamentos Pagos",
        value: String(overview.payments.paid_payments),
        description: `${formatMoney(overview.payments.paid_amount)} já liquidado`,
      },
      {
        title: "Pagamentos Gerados",
        value: String(overview.payments.total_payments),
        description: `${formatMoney(overview.payments.total_amount)} no total`,
      },
    ]
  }, [isFinancialUser, overview])

  return (
    <AppShell>
      <div className="space-y-6">
        <section className="rounded-2xl border bg-card p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <Badge variant="secondary">
                {isDashboardContextLoading
                  ? "Dashboard"
                  : isFinancialUser
                    ? "Dashboard Financeiro"
                    : "Dashboard Executivo"}
              </Badge>
              <div>
                <h2 className="text-2xl font-semibold tracking-tight lg:text-3xl">
                  {isDashboardContextLoading
                    ? "Carregando visão do painel"
                    : isFinancialUser
                      ? "Visão financeira de pagamentos"
                      : "Visão geral operacional"}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {isDashboardContextLoading
                    ? "Sincronizando seus indicadores e permissões de acesso."
                    : isFinancialUser
                      ? "Acompanhe o fluxo de pagamentos com foco em pendências, liquidações e volume total."
                      : "Acompanhe contratos, medições e pagamentos em uma única visão."}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {isDashboardContextLoading ? (
                <Button variant="outline" disabled>
                  Carregando...
                </Button>
              ) : isFinancialUser ? (
                <Link href="/payments" className={buttonVariants()}>
                  Ver pagamentos
                </Link>
              ) : (
                <Button>Novo contrato</Button>
              )}
              <Button variant="outline">Exportar relatório</Button>
            </div>
          </div>
        </section>

        {isDashboardContextLoading ? <DashboardCardsSkeleton /> : <OverviewCards cards={cards} />}

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_300px]">
          {isDashboardContextLoading ? (
            <Card className="shadow-sm">
              <CardContent className="space-y-3 py-6">
                <div className="h-5 w-40 animate-pulse rounded bg-muted" />
                <div className="h-28 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ) : isFinancialUser ? (
            <RecentPaymentsTable />
          ) : (
            <RecentContractsTable />
          )}

          <Card className="h-fit">
            <CardContent className="space-y-4 pt-6">
              <div>
                <p className="text-sm font-medium">Resumo rápido</p>
                <p className="text-sm text-muted-foreground">
                  {isDashboardContextLoading
                    ? "Carregando dados consolidados..."
                    : isFinancialUser
                    ? "Acompanhe o que precisa de baixa imediata e o que já foi liquidado."
                    : `${overview?.contracts.active_contracts ?? 0} contrato(s) ativo(s) na sua carteira.`}
                </p>
              </div>

              <div className="rounded-lg bg-primary/10 p-3">
                <p className="text-xs text-muted-foreground">
                  {isFinancialUser ? "Pendências" : "Atenção"}
                </p>
                <p className="text-sm font-medium">
                  {isDashboardContextLoading
                    ? "Carregando pendências..."
                    : isFinancialUser
                    ? `${overview?.payments.pending_payments ?? 0} pagamentos pendentes para tratar.`
                    : `${overview?.measurements.pending_measurements ?? 0} medições aguardando aprovação.`}
                </p>
              </div>

              <div className="rounded-lg bg-secondary p-3">
                <p className="text-xs text-muted-foreground">Financeiro</p>
                <p className="text-sm font-medium">
                  {isDashboardContextLoading
                    ? "Carregando situação financeira..."
                    : isFinancialUser
                    ? `${overview?.payments.failed_payments ?? 0} pagamentos com falha requerem ação.`
                    : `${overview?.payments.pending_payments ?? 0} pagamentos pendentes de baixa.`}
                </p>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </AppShell>
  )
}
