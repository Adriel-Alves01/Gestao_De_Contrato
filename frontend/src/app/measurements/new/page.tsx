import { Suspense } from "react"

import { AppShell } from "@/components/layout/app-shell"
import { NewMeasurementForm } from "@/features/measurements/components/new-measurement-form"

export default function NewMeasurementPage() {
  return (
    <AppShell>
      <Suspense fallback={<p className="text-sm text-muted-foreground">Carregando...</p>}>
        <NewMeasurementForm />
      </Suspense>
    </AppShell>
  )
}
