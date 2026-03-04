import { AppShell } from "@/components/layout/app-shell"
import { EditMeasurementForm } from "@/features/measurements/components/edit-measurement-form"

interface MeasurementEditPageProps {
  params: Promise<{
    id: string
  }>
}

export default async function MeasurementEditPage({ params }: MeasurementEditPageProps) {
  const { id } = await params

  return (
    <AppShell>
      <EditMeasurementForm measurementId={id} />
    </AppShell>
  )
}
