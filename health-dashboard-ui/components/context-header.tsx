"use client"

import { Home, Plane } from "lucide-react"
import { format } from "date-fns"

interface ContextHeaderProps {
  date: Date
  isTravel: boolean
  locationType: "Home" | "Hotel" | "Remote"
}

export function ContextHeader({ date, isTravel, locationType }: ContextHeaderProps) {
  return (
    <div className="sticky top-0 z-10 bg-background border-b border-border px-4 lg:px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{format(date, "EEEE, MMM d")}</h1>
          <p className="text-sm text-muted-foreground mt-1">Your adaptive schedule</p>
        </div>

        {isTravel ? (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--travel-bg)] text-[var(--travel-text)]">
            <Plane className="h-4 w-4" />
            <span className="font-medium text-sm">Travel Mode: {locationType}</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--home-bg)] text-[var(--home-text)]">
            <Home className="h-4 w-4" />
            <span className="font-medium text-sm">Home Base</span>
          </div>
        )}
      </div>
    </div>
  )
}
