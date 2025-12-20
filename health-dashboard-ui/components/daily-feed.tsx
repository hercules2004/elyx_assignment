"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCw, Clock, MapPin, AlertCircle, Archive, SkipForward } from "lucide-react"

interface Activity {
  id: string
  name: string
  type: string
  priority: number
  duration_minutes: number
  is_backup: boolean
  backup_activity_ids: string[]
  start_time?: string
  prep_duration_minutes?: number
  location?: string
}

interface DailyFeedProps {
  activities: Activity[]
  failedActivities: any[]
  onSwap: (activityId: string) => void
}

export function DailyFeed({ activities, failedActivities, onSwap }: DailyFeedProps) {
  // Helper to format time string (HH:MM:SS) to readable time (e.g. 9:00 AM)
  const formatTime = (timeStr?: string) => {
    if (!timeStr) return ""
    const [hours, minutes] = timeStr.split(":").map(Number)
    const date = new Date()
    date.setHours(hours, minutes)
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  }

  // Helper to calculate end time
  const getEndTime = (startStr?: string, duration?: number) => {
    if (!startStr || !duration) return ""
    const [hours, minutes] = startStr.split(":").map(Number)
    const date = new Date()
    date.setHours(hours, minutes + duration)
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
  }

  // Helper to format rescheduled date
  const formatRescheduledDate = (dateStr: string) => {
    const date = new Date(dateStr + "T00:00:00") // Add time to avoid timezone issues
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  }

  // Group failures by category
  const replaced = failedActivities.filter((f) => f.category === "replaced")
  const rescheduled = failedActivities.filter((f) => f.category === "rescheduled")
  const skipped = failedActivities.filter((f) => f.category === "skipped")
  const failed = failedActivities.filter((f) => f.category === "failed")

  return (
    <div className="space-y-6">
      {/* Scheduled Activities */}
      <div className="space-y-4">
        {activities.map((activity, index) => {
          const startTime = formatTime(activity.start_time)
          const endTime = getEndTime(activity.start_time, activity.duration_minutes)
          return (
            <Card key={`${activity.id}-${index}`} className={activity.is_backup ? "border-l-4 border-l-amber-400" : ""}>
              <CardContent className="p-4 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{activity.name}</h3>
                    {activity.is_backup && (
                      <Badge variant="secondary" className="text-xs bg-amber-100 text-amber-800 hover:bg-amber-100">
                        Backup
                      </Badge>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    {activity.start_time && (
                      <span className="flex items-center gap-1 font-medium text-foreground/80">
                        <Clock className="h-3.5 w-3.5" />
                        {startTime} - {endTime}
                      </span>
                    )}
                    <span className="flex items-center gap-1">Duration: {activity.duration_minutes}m</span>
                    {activity.prep_duration_minutes ? (
                      <span className="flex items-center gap-1 text-xs bg-muted px-1.5 py-0.5 rounded">
                        +{activity.prep_duration_minutes}m prep
                      </span>
                    ) : null}
                    {activity.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5" />
                        {activity.location}
                      </span>
                    )}
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => onSwap(activity.id)}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          )
        })}
        {activities.length === 0 && <p className="text-muted-foreground text-center py-8">No activities scheduled.</p>}
      </div>

      {/* Failures & Skips Section */}
      {(failed.length > 0 || rescheduled.length > 0 || skipped.length > 0 || replaced.length > 0) && (
        <div className="space-y-4 pt-4 border-t">
          {/* Replaced by Backup (Blue) */}
          {replaced.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Replaced by Backup ({replaced.length})</h3>
              {replaced.map((f) => (
                <div key={f.activity_id} className="flex items-center gap-3 text-sm p-3 rounded-md bg-blue-50 text-blue-900 border border-blue-100">
                  <Archive className="h-4 w-4 shrink-0" />
                  <div className="flex-1">
                    <span className="font-medium">{f.activity_name}</span>
                    <span className="block text-xs opacity-90">Reason: {f.reason}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Rescheduled (Amber) */}
          {rescheduled.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Rescheduled ({rescheduled.length})</h3>
              {rescheduled.map((f) => (
                <div key={f.activity_id} className="flex items-center gap-3 text-sm p-3 rounded-md bg-amber-50 text-amber-900 border border-amber-100">
                  <Clock className="h-4 w-4 shrink-0" />
                  <div className="flex-1">
                    <span className="font-medium">{f.activity_name}</span>
                    <span className="block text-xs opacity-90">
                      {f.rescheduledTo
                        ? `Rescheduled to ${formatRescheduledDate(f.rescheduledTo)}`
                        : "Rescheduled"}. Reason: {f.reason}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Truly Failed & Skipped (Red & Gray) */}
          {(failed.length > 0 || skipped.length > 0) && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Skipped & Unscheduled ({failed.length + skipped.length})</h3>
              {failed.map((f) => (
                <div key={f.activity_id} className="flex items-center gap-3 text-sm p-3 rounded-md bg-red-50 text-red-900 border border-red-100">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <div className="flex-1">
                    <span className="font-medium">{f.activity_name}</span>
                    <span className="block text-xs opacity-90">Failed: {f.reason}</span>
                  </div>
                </div>
              ))}
              {skipped.map((f) => (
                <div key={f.activity_id} className="flex items-center gap-3 text-sm p-3 rounded-md bg-muted/50 text-muted-foreground border">
                  <SkipForward className="h-4 w-4 shrink-0" />
                  <div className="flex-1">
                    <span className="font-medium">{f.activity_name}</span>
                    <span className="block text-xs opacity-90">Skipped: {f.reason}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
