"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getContract, updateContract, uploadContractAttachments } from "@/services/api/contracts"

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
  numero_contrato: string
  empresa_contratante: string
  empresa_contratada: string
  cnpj_empresa_contratada: string
  cnpj_empresa_contratante: string
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
  const [additionalFiles, setAdditionalFiles] = useState<File[]>([])
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
          numero_contrato: contract.numero_contrato ?? "",
          empresa_contratante: contract.empresa_contratante ?? "",
          empresa_contratada: contract.empresa_contratada ?? "",
          cnpj_empresa_contratada: contract.cnpj_empresa_contratada ?? "",
          cnpj_empresa_contratante: contract.cnpj_empresa_contratante ?? "",
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

    if (formData.start_date && formData.end_date && formData.end_date < formData.start_date) {
      setError("A data de fim não pode ser anterior à data de início.")
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
        numero_contrato: formData.numero_contrato || undefined,
        empresa_contratante: formData.empresa_contratante || undefined,
        empresa_contratada: formData.empresa_contratada || undefined,
        cnpj_empresa_contratada: formData.cnpj_empresa_contratada || undefined,
        cnpj_empresa_contratante: formData.cnpj_empresa_contratante || undefined,
      })

      if (additionalFiles.length > 0) {
        await uploadContractAttachments(Number(contractId), additionalFiles)
      }

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
        <p className="text-sm text-muted-foreground">
          Atualize os dados do contrato selecionado.
        </p>
      </section>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Dados do contrato</CardTitle>
        </CardHeader>

        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            {/* Linha 1: Título, Número, Datas */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
              <label className="space-y-2">
                <span className="text-sm font-medium">Título *</span>
                <input
                  required
                  name="title"
                  value={formData.title}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                  placeholder="Ex.: Contrato de Manutenção Predial"
                />
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium">Número do contrato</span>
                <input
                  type="text"
                  name="numero_contrato"
                  value={formData.numero_contrato}
                  onChange={handleFieldChange}
                  className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                  placeholder="Ex.: CTR-2024-001"
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

            {/* Descrição */}
            <label className="space-y-2">
              <span className="text-sm font-medium">Descrição</span>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleFieldChange}
                rows={4}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                placeholder="Detalhes do contrato"
              />
            </label>

            {/* Documentos adicionais */}
            <label className="space-y-2">
              <span className="text-sm font-medium">Anexar PDFs adicionais</span>
              <input
                type="file"
                accept="application/pdf"
                multiple
                onChange={(e) => setAdditionalFiles(Array.from(e.target.files ?? []))}
                className="h-10 w-full rounded-md border bg-background px-3 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-l-md file:border-0 file:bg-muted file:text-sm file:font-medium hover:file:bg-muted/80"
              />
              {additionalFiles.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {additionalFiles.length} arquivo{additionalFiles.length > 1 ? "s" : ""} selecionado{additionalFiles.length > 1 ? "s" : ""}: {additionalFiles.map((f) => f.name).join(", ")}
                </p>
              )}
            </label>

            {/* Valor, Manager, Status */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
                  placeholder="Ex.: 50000 ou 50.000,00"
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
                  placeholder="Ex.: 3"
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
                  <option value="ACTIVE">Ativo</option>
                  <option value="CLOSED">Fechado</option>
                </select>
              </label>
            </div>

            {/* Dados das Empresas */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <h3 className="mb-4 font-medium">Dados das Empresas</h3>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-medium">Empresa contratada</span>
                    <input
                      type="text"
                      name="empresa_contratada"
                      value={formData.empresa_contratada}
                      onChange={handleFieldChange}
                      className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                      placeholder="Ex.: Prestadora XYZ S.A."
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium">CNPJ contratada</span>
                    <input
                      type="text"
                      name="cnpj_empresa_contratada"
                      value={formData.cnpj_empresa_contratada}
                      onChange={handleFieldChange}
                      className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                      placeholder="Ex.: 12.345.678/0001-90"
                    />
                  </label>
                </div>
              </div>

              <div>
                <div className="mb-4 h-6" />
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-sm font-medium">Empresa contratante</span>
                    <input
                      type="text"
                      name="empresa_contratante"
                      value={formData.empresa_contratante}
                      onChange={handleFieldChange}
                      className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                      placeholder="Ex.: Empresa ABC Ltda"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-sm font-medium">CNPJ contratante</span>
                    <input
                      type="text"
                      name="cnpj_empresa_contratante"
                      value={formData.cnpj_empresa_contratante}
                      onChange={handleFieldChange}
                      className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                      placeholder="Ex.: 98.765.432/0001-10"
                    />
                  </label>
                </div>
              </div>
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
              <Link
                href={`/contracts/${contractId}`}
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
