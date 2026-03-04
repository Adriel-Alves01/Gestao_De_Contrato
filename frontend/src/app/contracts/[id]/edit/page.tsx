import { AppShell } from "@/components/layout/app-shell"
import { EditContractForm } from "@/features/contracts/components/edit-contract-form"

interface ContractEditPageProps {
  params: Promise<{
    id: string
  }>
}

export default async function ContractEditPage({ params }: ContractEditPageProps) {
  const { id } = await params

  return (
    <AppShell>
      <EditContractForm contractId={id} />
    </AppShell>
  )
}
