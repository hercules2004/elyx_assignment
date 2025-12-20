"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  format,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  startOfWeek,
  endOfWeek,
} from "date-fns"

interface DayContext {
  date: string
  is_traveling: boolean
  location_type: "Home" | "Hotel" | "Remote"
  load_intensity: "Low" | "Medium" | "High"
}

interface SmartCalendarProps {
  selectedDate: Date
  onSelectDate: (date: Date) => void
  dayContexts: Record<string, DayContext>
}

const getLoadColor = (intensity: "Low" | "Medium" | "High") => {
  switch (intensity) {
    case "High":
      return "bg-[var(--load-high)]"
    case "Medium":
      return "bg-[var(--load-medium)]"
    case "Low":
      return "bg-[var(--load-low)]"
  }
}

export function SmartCalendar({ selectedDate, onSelectDate, dayContexts }: SmartCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(selectedDate)

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const calendarStart = startOfWeek(monthStart)
  const calendarEnd = endOfWeek(monthEnd)

  const days = eachDayOfInterval({ start: calendarStart, end: calendarEnd })
  const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

  const formatDateKey = (date: Date) => {
    return format(date, "yyyy-MM-dd")
  }

  const getDayContext = (date: Date) => {
    return dayContexts[formatDateKey(date)]
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-lg">{format(currentMonth, "MMMM yyyy")}</h2>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="h-8 w-8"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {weekDays.map((day) => (
          <div key={day} className="text-center text-xs font-medium text-muted-foreground py-2">
            {day}
          </div>
        ))}

        {days.map((day) => {
          const dayContext = getDayContext(day)
          const isCurrentMonth = isSameMonth(day, currentMonth)
          const isSelected = isSameDay(day, selectedDate)
          const isToday = isSameDay(day, new Date())

          return (
            <button
              key={day.toString()}
              onClick={() => onSelectDate(day)}
              disabled={!isCurrentMonth}
              className={`
                relative aspect-square p-2 rounded-md text-sm transition-colors
                ${!isCurrentMonth ? "text-muted-foreground/40 cursor-not-allowed" : ""}
                ${isSelected ? "bg-primary text-primary-foreground font-semibold" : ""}
                ${!isSelected && isCurrentMonth ? "hover:bg-accent" : ""}
                ${dayContext?.is_traveling && !isSelected ? "bg-[var(--travel-bg)]" : ""}
                ${isToday && !isSelected ? "ring-2 ring-primary ring-inset" : ""}
              `}
            >
              <span className="block">{format(day, "d")}</span>
              {dayContext && isCurrentMonth && (
                <div className="absolute bottom-1 left-1/2 -translate-x-1/2">
                  <div className={`w-1.5 h-1.5 rounded-full ${getLoadColor(dayContext.load_intensity)}`} />
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
