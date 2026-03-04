import { AppShell } from "@/components/layout/app-shell"
import { PaymentDetailPageContent } from "@/features/payments/components/payment-detail-page-content"

interface PaymentDetailPageProps {
  params: Promise<{
    id: string
  }>
}

export default async function PaymentDetailPage({ params }: PaymentDetailPageProps) {
  const { id } = await params

  return (
    <AppShell>
      <PaymentDetailPageContent paymentId={id} />
    </AppShell>
  )
}
