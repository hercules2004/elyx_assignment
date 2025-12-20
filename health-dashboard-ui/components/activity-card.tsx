"use client"

import { Dumbbell, Pill, Heart, RefreshCw } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface Activity {
  id: string
  name: string
  type: string
  priority: number
  duration_minutes: number
  is_backup: boolean
  backup_activity_ids: string[]
}

interface ActivityCardProps {
  activity: Activity
  onSwap: (activityId: string) => void
}

const getIconForType = (type: string) => {
  switch (type) {
    case "Fitness":
      return Dumbbell
    case "Medication":
      return Pill
    case "Wellness":
      return Heart
    default:
      return Heart
  }
}

export function ActivityCard({ activity, onSwap }: ActivityCardProps) {
  const Icon = getIconForType(activity.type)

  return (
    <Card className={`p-4 ${activity.is_backup ? "border-[var(--backup-border)] border-2 bg-primary/5" : ""}`}>
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${activity.is_backup ? "bg-primary/10" : "bg-secondary"}`}>
          <Icon className={`h-5 w-5 ${activity.is_backup ? "text-primary" : "text-foreground"}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-base">{activity.name}</h3>
            {activity.is_backup && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">Plan B</span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {activity.duration_minutes} mins • Priority P{activity.priority}
          </p>
        </div>

        {activity.backup_activity_ids.length > 0 && (
          <Button variant="outline" size="sm" onClick={() => onSwap(activity.id)} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            <span className="hidden sm:inline">Swap</span>
          </Button>
        )}
      </div>
    </Card>
  )
}
