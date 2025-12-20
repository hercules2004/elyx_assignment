"use client"

import { useState, useEffect } from "react"
import type { DashboardData } from "@/types/scheduler"

export function useSchedulerData() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch("/dashboard_data.json")
        if (!response.ok) throw new Error("Failed to fetch dashboard data")
        const jsonData = await response.json()
        setData(jsonData)
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Unknown error"))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return { data, loading, error }
}