import { AppShell } from "@/components/layout/app-shell"
import { ContractDetailPageContent } from "@/features/contracts/components/contract-detail-page-content"

interface ContractDetailPageProps {
  params: Promise<{
    id: string
  }>
}

export default async function ContractDetailPage({ params }: ContractDetailPageProps) {
  const { id } = await params

  return (
    <AppShell>
      <ContractDetailPageContent contractId={id} />
    </AppShell>
  )
}
