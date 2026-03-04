"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getMeasurement, updateMeasurement } from "@/services/api/measurements"

interface EditMeasurementFormProps {
  measurementId: string
}

interface MeasurementFormState {
  contract: string
  description: string
  value: string
  status: "PENDING" | "APPROVED" | "REJECTED"
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

export function EditMeasurementForm({ measurementId }: EditMeasurementFormProps) {
  const router = useRouter()
  const [formData, setFormData] = useState<MeasurementFormState | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadMeasurement = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const measurement = await getMeasurement(Number(measurementId))
        setFormData({
          contract: String(measurement.contract),
          description: measurement.description,
          value: measurement.value,
          status: measurement.status,
        })
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Não foi possível carregar a medição"
        )
      } finally {
        setIsLoading(false)
      }
    }

    void loadMeasurement()
  }, [measurementId])

  const handleFieldChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
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

    try {
      setIsSubmitting(true)

      await updateMeasurement(Number(measurementId), {
        contract: parsedContractId,
        description: formData.description,
        value: parsedValue,
      })

      router.push(`/measurements/${measurementId}`)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Não foi possível atualizar a medição"
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando medição...</p>
  }

  if (!formData) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">Medição não encontrada.</p>
        <Link href="/measurements" className={buttonVariants({ variant: "outline" })}>
          Voltar para medições
        </Link>
      </div>
    )
  }

  const canEditMeasurement = formData.status === "PENDING"

  if (!canEditMeasurement) {
    return (
      <div className="space-y-6">
        <section className="rounded-2xl border bg-card p-6 shadow-sm">
          <h2 className="text-2xl font-semibold tracking-tight">Editar medição</h2>
        </section>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Edição bloqueada</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Esta medição está {formData.status} e não pode ser editada.
            </p>

            <div className="flex items-center gap-2">
              <Link href={`/measurements/${measurementId}`} className={buttonVariants()}>
                Voltar para detalhes
              </Link>
              <Link href="/measurements" className={buttonVariants({ variant: "outline" })}>
                Voltar para medições
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <h2 className="text-2xl font-semibold tracking-tight">Editar medição</h2>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Dados da medição</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
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
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Valor *</span>
                <input
                  required
                  type="text"
                  inputMode="decimal"
                  name="value"
                  value={formData.value}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                />
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

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <div className="flex items-center gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Salvando..." : "Salvar alterações"}
              </Button>
              <Link href={`/measurements/${measurementId}`} className={buttonVariants({ variant: "outline" })}>
                Cancelar
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
