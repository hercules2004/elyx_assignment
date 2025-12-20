"use client"

import { useState } from "react"
import { ContextHeader } from "@/components/context-header"
import { SmartCalendar } from "@/components/smart-calendar"
import { DailyFeed } from "@/components/daily-feed"
import { SwapModal } from "@/components/swap-modal"
import { Button } from "@/components/ui/button"
import { Menu, X } from "lucide-react"
import { useSchedulerData } from "@/hooks/use-scheduler-data"
import type { Activity, TimeSlot } from "@/models"

export default function ResilientHealthDashboard() {
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [swapModalOpen, setSwapModalOpen] = useState(false)
  const [selectedActivityForSwap, setSelectedActivityForSwap] = useState<string | null>(null)
  const [mobileCalendarOpen, setMobileCalendarOpen] = useState(false)
  
  const { data, loading } = useSchedulerData()

  if (loading || !data) {
    return <div className="flex h-screen items-center justify-center">Loading scheduler data...</div>
  }

  // Pre-compute a map of all scheduled primary activity IDs to their dates
  const scheduledDatesMap = new Map<string, string[]>()
  Object.values(data.schedule).flat().forEach((slot) => {
    if (!slot.is_backup) {
      const dates = scheduledDatesMap.get(slot.activity_id) || []
      dates.push(slot.date)
      scheduledDatesMap.set(slot.activity_id, dates)
    }
  })

  // Helper to format date as YYYY-MM-DD (Local Time)
  const formatDate = (d: Date) => {
    const offset = d.getTimezoneOffset()
    const local = new Date(d.getTime() - (offset * 60 * 1000))
    return local.toISOString().split('T')[0]
  }

  // Get data for selected date
  const dateKey = formatDate(selectedDate)
  const dayContext = data.context[dateKey] || {
    date: dateKey,
    is_traveling: false,
    location_type: "Home",
    load_intensity: "Low" as const,
  }

  const slots = data.schedule[dateKey] || []

  // Create a set of activity IDs that are either scheduled or have a backup scheduled
  const satisfiedActivityIds = new Set<string>()
  slots.forEach((slot) => {
    satisfiedActivityIds.add(slot.activity_id)
    if (slot.original_activity_id) {
      satisfiedActivityIds.add(slot.original_activity_id)
    }
  })

  const activities = slots.map((slot: TimeSlot) => {
    const activity = data.activities[slot.activity_id]
    if (!activity) return null
    return {
      ...activity,
      is_backup: slot.is_backup,
      start_time: slot.start_time,
      prep_duration_minutes: slot.prep_duration_minutes,
    }
  }).filter(Boolean) as (Activity & { is_backup: boolean; start_time: string; prep_duration_minutes: number })[]

  const rawFailures = data.failures[dateKey] || []
  const uniqueFailuresMap = new Map<string, any>()

  rawFailures.forEach((failure) => {
    // If the activity was scheduled as a PRIMARY on THIS day, or already processed, ignore the failure log for it.
    const wasScheduledAsPrimaryToday = slots.some(s => !s.is_backup && s.activity_id === failure.activity_id);
    if (wasScheduledAsPrimaryToday || uniqueFailuresMap.has(failure.activity_id)) {
      return
    }

    const activity = data.activities[failure.activity_id]
    const enrichedReason = failure.reason.replace(/\b(act_\w+)\b/g, (match) => {
      return data.activities[match]?.name || match
    })

    let category = "failed" // Default category
    let rescheduledTo: string | undefined
    const wasReplacedByBackupToday = slots.some(s => s.is_backup && s.original_activity_id === failure.activity_id);

    if (wasReplacedByBackupToday) {
      category = "replaced"
    } else if (failure.type === "Travel") {
      category = "skipped"
    } else if (scheduledDatesMap.has(failure.activity_id)) {
      // Find the first scheduled date that is AFTER the current date
      const dates = scheduledDatesMap.get(failure.activity_id)!.sort()
      const nextDate = dates.find((d) => d > dateKey)
      
      if (nextDate) {
        category = "rescheduled"
        rescheduledTo = nextDate
      }
    }

    uniqueFailuresMap.set(failure.activity_id, {
      ...failure,
      reason: enrichedReason,
      activity_name: activity ? activity.name : failure.activity_id,
      category,
      rescheduledTo,
    })
  })
  const failedActivities = Array.from(uniqueFailuresMap.values())

  // Handle swap button click
  const handleSwap = (activityId: string) => {
    setSelectedActivityForSwap(activityId)
    setSwapModalOpen(true)
  }

  // Handle swap confirmation
  const handleConfirmSwap = () => {
    console.log("[v0] Swap confirmed for activity:", selectedActivityForSwap)
    // TODO: Implement swap logic when backend is connected
    setSelectedActivityForSwap(null)
  }

  // Get backup activity for modal
  const originalActivity = selectedActivityForSwap ? data.activities[selectedActivityForSwap] : null
  const backupActivity = originalActivity?.backup_activity_ids[0]
    ? data.activities[originalActivity.backup_activity_ids[0]]
    : null

  return (
    <div className="min-h-screen bg-background">
      {/* Context Header */}
      <ContextHeader date={selectedDate} isTravel={dayContext.is_traveling} locationType={dayContext.location_type} />

      {/* Main Layout */}
      <div className="flex flex-col lg:flex-row lg:h-[calc(100vh-89px)]">
        {/* Mobile Calendar Toggle */}
        <div className="lg:hidden p-4 border-b border-border">
          <Button variant="outline" onClick={() => setMobileCalendarOpen(!mobileCalendarOpen)} className="w-full gap-2">
            {mobileCalendarOpen ? (
              <>
                <X className="h-4 w-4" />
                Hide Calendar
              </>
            ) : (
              <>
                <Menu className="h-4 w-4" />
                Show Calendar
              </>
            )}
          </Button>
        </div>

        {/* Sidebar / Calendar */}
        <aside
          className={`
          lg:w-96 lg:border-r lg:border-border lg:block lg:overflow-y-auto
          ${mobileCalendarOpen ? "block" : "hidden"}
          p-4 lg:p-6
        `}
        >
          <SmartCalendar
            selectedDate={selectedDate}
            onSelectDate={(date) => {
              setSelectedDate(date)
              setMobileCalendarOpen(false)
            }}
            dayContexts={data.context}
          />
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <div className="max-w-3xl">
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-1">Daily Activities</h2>
              <p className="text-sm text-muted-foreground">{activities.length} activities scheduled</p>
            </div>

            <DailyFeed
              activities={activities}
              failedActivities={failedActivities}
              onSwap={handleSwap}
            />
          </div>
        </main>
      </div>

      {/* Swap Modal */}
      <SwapModal
        open={swapModalOpen}
        onOpenChange={setSwapModalOpen}
        originalActivity={originalActivity}
        backupActivity={backupActivity}
        onConfirmSwap={handleConfirmSwap}
      />
    </div>
  )
}
