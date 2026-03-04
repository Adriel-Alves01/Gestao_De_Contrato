import { AppShell } from "@/components/layout/app-shell"
import { MeasurementDetailPageContent } from "@/features/measurements/components/measurement-detail-page-content"

interface MeasurementDetailPageProps {
  params: Promise<{
    id: string
  }>
}

export default async function MeasurementDetailPage({ params }: MeasurementDetailPageProps) {
  const { id } = await params

  return (
    <AppShell>
      <MeasurementDetailPageContent measurementId={id} />
    </AppShell>
  )
}
