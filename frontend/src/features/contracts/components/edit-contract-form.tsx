"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getContract, updateContract } from "@/services/api/contracts"

interface EditContractFormProps {
  contractId: string
}

interface ContractFormState {
  title: string
  description: string
  total_value: string
  manager_id: string
  start_date: string
  end_date: string
  status: "ACTIVE" | "CLOSED"
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

export function EditContractForm({ contractId }: EditContractFormProps) {
  const router = useRouter()
  const [formData, setFormData] = useState<ContractFormState | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadContract = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const parsedId = Number(contractId)
        const contract = await getContract(parsedId)

        setFormData({
          title: contract.title,
          description: contract.description,
          total_value: contract.total_value,
          manager_id: contract.manager?.id ? String(contract.manager.id) : "",
          start_date: contract.start_date,
          end_date: contract.end_date,
          status: contract.status,
        })
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Não foi possível carregar o contrato"
        )
      } finally {
        setIsLoading(false)
      }
    }

    void loadContract()
  }, [contractId])

  const handleFieldChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = event.target
    setFormData((previousState) => {
      if (!previousState) {
        return previousState
      }

      return {
        ...previousState,
        [name]: value,
      }
    })
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!formData) {
      return
    }

    const parsedTotalValue = parseMoneyInput(formData.total_value)
    if (parsedTotalValue === null || parsedTotalValue <= 0) {
      setError("Informe um valor total válido. Ex.: 50000 ou 50.000,00")
      return
    }

    try {
      setIsSubmitting(true)

      await updateContract(Number(contractId), {
        title: formData.title,
        description: formData.description,
        total_value: parsedTotalValue,
        manager_id: formData.manager_id ? Number(formData.manager_id) : undefined,
        start_date: formData.start_date,
        end_date: formData.end_date,
        status: formData.status,
      })

      router.push(`/contracts/${contractId}`)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Não foi possível atualizar o contrato"
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando contrato...</p>
  }

  if (!formData) {
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
        <h2 className="text-2xl font-semibold tracking-tight">Editar contrato</h2>
        <p className="text-sm text-muted-foreground">Atualize os dados do contrato selecionado.</p>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Dados do contrato</CardTitle>
        </CardHeader>

        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium">Título *</span>
                <input
                  required
                  name="title"
                  value={formData.title}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Status</span>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="CLOSED">CLOSED</option>
                </select>
              </label>
            </div>

            <label className="space-y-2">
              <span className="text-sm font-medium">Descrição</span>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleFieldChange}
                rows={4}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </label>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
              <label className="space-y-2">
                <span className="text-sm font-medium">Valor total *</span>
                <input
                  required
                  type="text"
                  inputMode="decimal"
                  name="total_value"
                  value={formData.total_value}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Manager (ID) opcional</span>
                <input
                  type="number"
                  min="1"
                  step="1"
                  name="manager_id"
                  value={formData.manager_id}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Data início *</span>
                <input
                  required
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Data fim *</span>
                <input
                  required
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>
            </div>

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <div className="flex items-center gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Salvando..." : "Salvar alterações"}
              </Button>
              <Link href={`/contracts/${contractId}`} className={buttonVariants({ variant: "outline" })}>
                Cancelar
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
