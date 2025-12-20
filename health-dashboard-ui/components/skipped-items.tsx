"use client"

import { AlertTriangle, ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import { Card } from "@/components/ui/card"

interface FailedActivity {
  activity_name: string
  reason: string
  priority: number
}

interface SkippedItemsProps {
  failedActivities: FailedActivity[]
}

export function SkippedItems({ failedActivities }: SkippedItemsProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (failedActivities.length === 0) return null

  return (
    <div className="mt-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-3 w-full"
      >
        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <AlertTriangle className="h-4 w-4 text-destructive" />
        <span className="font-medium text-sm">Not Scheduled / Skipped ({failedActivities.length})</span>
      </button>

      {isExpanded && (
        <div className="space-y-2">
          {failedActivities.map((failed, index) => (
            <Card key={index} className="p-4 bg-muted/50 border-dashed">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-destructive/10 mt-0.5">
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm text-muted-foreground line-through mb-1">
                    {failed.activity_name}
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-destructive">Blocked:</span> {failed.reason}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Priority P{failed.priority}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
