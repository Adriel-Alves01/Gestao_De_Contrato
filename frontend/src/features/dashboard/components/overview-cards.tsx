import { Activity, FileText, Wallet } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { overviewCards } from "@/features/dashboard/constants/overview"

interface OverviewCardData {
  title: string
  value: string
  description: string
}

const cardIcons = [FileText, Activity, Wallet]

interface OverviewCardsProps {
  cards?: OverviewCardData[]
}

export function OverviewCards({ cards = overviewCards }: OverviewCardsProps) {
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {cards.map((card, index) => {
        const Icon = cardIcons[index]

        return (
        <Card key={card.title} className="shadow-sm">
          <CardHeader>
            <div className="flex items-start justify-between">
              <CardDescription>{card.title}</CardDescription>
              {Icon ? (
                <span className="rounded-md bg-primary/10 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </span>
              ) : null}
            </div>
            <CardTitle className="text-2xl">{card.value}</CardTitle>
          </CardHeader>
          <CardContent className="pb-6">
            <p className="text-sm text-muted-foreground">{card.description}</p>
          </CardContent>
        </Card>
      )})}
    </section>
  )
}
