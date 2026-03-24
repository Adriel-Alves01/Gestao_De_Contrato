"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"

import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getContract } from "@/services/api/contracts"
import { createMeasurement } from "@/services/api/measurements"

interface MeasurementFormState {
  contract: string
  description: string
  value: string
  start_date: string
  end_date: string
}

const initialFormState: MeasurementFormState = {
  contract: "",
  description: "",
  value: "",
  start_date: "",
  end_date: "",
}

function parseMoneyInput(value: string): number | null {
  const rawValue = value.trim().replace(/\s/g, "")
  if (!rawValue) {
    return null
  }

  const noCurrency = rawValue.replace(/[R$]/g, "")
  const onlyDotsAsThousands = /^\d{1,3}(\.\d{3})+$/.test(noCurrency)
  const onlyCommasAsThousands = /^\d{1,3}(,\d{3})+$/.test(noCurrency)

  let normalizedValue = noCurrency

  if (onlyDotsAsThousands) {
    normalizedValue = noCurrency.replace(/\./g, "")
  } else if (onlyCommasAsThousands) {
    normalizedValue = noCurrency.replace(/,/g, "")
  } else {
    normalizedValue = noCurrency.replace(/\./g, "").replace(",", ".")
  }

  const parsedNumber = Number(normalizedValue)
  return Number.isFinite(parsedNumber) ? parsedNumber : null
}

export function NewMeasurementForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const contractParam = searchParams.get("contract") ?? ""

  const [formData, setFormData] = useState<MeasurementFormState>({
    ...initialFormState,
    contract: contractParam,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [contractTitle, setContractTitle] = useState<string | null>(null)
  const [remainingBalance, setRemainingBalance] = useState<number | null>(null)
  const [contractTitleLoading, setContractTitleLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const contractId = Number(formData.contract)

    if (!Number.isInteger(contractId) || contractId <= 0) {
      setContractTitle(null)
      return
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(async () => {
      setContractTitleLoading(true)
      try {
        const contract = await getContract(contractId)
        setContractTitle(contract.title)
        setRemainingBalance(Number(contract.remaining_balance))
      } catch {
        setContractTitle(null)
        setRemainingBalance(null)
      } finally {
        setContractTitleLoading(false)
      }
    }, 500)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [formData.contract])

  const handleFieldChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = event.target
    setFormData((previousState) => ({
      ...previousState,
      [name]: value,
    }))
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const parsedValue = parseMoneyInput(formData.value)
    const parsedContractId = Number(formData.contract)

    if (!Number.isInteger(parsedContractId) || parsedContractId <= 0) {
      setError("Informe um ID de contrato válido.")
      return
    }

    if (parsedValue === null || parsedValue <= 0) {
      setError("Informe um valor válido. Ex.: 50000 ou 50.000,00")
      return
    }

    if (remainingBalance !== null && parsedValue > remainingBalance) {
      setError(
        `O valor da medição (${new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(parsedValue)}) ` +
        `é maior que o saldo restante do contrato (${new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(remainingBalance)}).`
      )
      return
    }

    if (formData.start_date && formData.end_date && formData.end_date < formData.start_date) {
      setError("A data de fim não pode ser anterior à data de início.")
      return
    }

    try {
      setIsSubmitting(true)

      await createMeasurement({
        contract: parsedContractId,
        description: formData.description,
        value: parsedValue,
        start_date: formData.start_date || null,
        end_date: formData.end_date || null,
      })

      router.push(contractParam ? `/contracts/${contractParam}` : "/measurements")
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Não foi possível criar a medição"
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <h2 className="text-2xl font-semibold tracking-tight">Nova medição</h2>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Dados da medição</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            {/* Linha 1: Contrato ID + Título */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium">Contrato (ID) *</span>
                <input
                  required
                  type="number"
                  min="1"
                  step="1"
                  name="contract"
                  value={formData.contract}
                  onChange={handleFieldChange}
                  readOnly={!!contractParam}
                  className={`h-10 w-full rounded-md border px-3 text-sm ${
                    contractParam
                      ? "bg-muted text-muted-foreground cursor-not-allowed"
                      : "bg-background"
                  }`}
                  placeholder="Ex.: 12"
                />
              </label>

              <div className="space-y-2">
                <span className="text-sm font-medium">Título do contrato</span>
                <div className="flex h-10 w-full items-center rounded-md border bg-muted px-3 text-sm text-muted-foreground">
                  {contractTitleLoading ? (
                    <span className="italic">Buscando...</span>
                  ) : contractTitle ? (
                    <span className="truncate">{contractTitle}</span>
                  ) : (
                    <span className="italic opacity-60">Preenchido automaticamente</span>
                  )}
                </div>
                {remainingBalance !== null && (
                  <p className="text-xs text-muted-foreground">
                    Saldo restante:{" "}
                    <span className="font-medium text-foreground">
                      {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(remainingBalance)}
                    </span>
                  </p>
                )}
              </div>
            </div>

            {/* Linha 2: Início + Fim */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium">Início</span>
                <input
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Fim</span>
                <input
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>
            </div>

            {/* Linha 3: Valor */}
            <label className="block space-y-2 md:max-w-xs">
              <span className="text-sm font-medium">Valor *</span>
              <input
                required
                type="text"
                inputMode="decimal"
                name="value"
                value={formData.value}
                onChange={handleFieldChange}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                placeholder="Ex.: 50000 ou 50.000,00"
              />
            </label>

            {/* Linha 4: Descrição */}
            <label className="space-y-2">
              <span className="text-sm font-medium">Descrição</span>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleFieldChange}
                rows={4}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                placeholder="Detalhes da medição"
              />
            </label>

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <div className="flex items-center gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Salvando..." : "Salvar medição"}
              </Button>
              <Link
                href={contractParam ? `/contracts/${contractParam}` : "/measurements"}
                className={buttonVariants({ variant: "outline" })}
              >
                Cancelar
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
