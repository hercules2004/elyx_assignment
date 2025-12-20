// TODO: Connect to backend API here
// This mock data structure matches the Pydantic models from the Python backend

export const mockActivities = {
  "act-1": {
    id: "act-1",
    name: "Morning Meds",
    type: "Medication",
    priority: 1,
    duration_minutes: 5,
    is_backup: false,
    backup_activity_ids: [],
  },
  "act-2": {
    id: "act-2",
    name: "Heavy Weightlifting",
    type: "Fitness",
    priority: 2,
    duration_minutes: 60,
    is_backup: false,
    backup_activity_ids: ["act-3"],
  },
  "act-3": {
    id: "act-3",
    name: "Bodyweight Flow",
    type: "Fitness",
    priority: 3,
    duration_minutes: 30,
    is_backup: true,
    backup_activity_ids: [],
  },
  "act-4": {
    id: "act-4",
    name: "Evening Supplements",
    type: "Medication",
    priority: 2,
    duration_minutes: 5,
    is_backup: false,
    backup_activity_ids: [],
  },
  "act-5": {
    id: "act-5",
    name: "Meditation",
    type: "Wellness",
    priority: 4,
    duration_minutes: 20,
    is_backup: false,
    backup_activity_ids: [],
  },
}

// Generate dates for the current month
const today = new Date()
const year = today.getFullYear()
const month = today.getMonth()

export const mockDayContexts = {
  // Today - Travel Mode
  [formatDate(today)]: {
    date: formatDate(today),
    is_traveling: true,
    location_type: "Hotel",
    load_intensity: "Medium",
  },
  // Yesterday - Home
  [formatDate(new Date(year, month, today.getDate() - 1))]: {
    date: formatDate(new Date(year, month, today.getDate() - 1)),
    is_traveling: false,
    location_type: "Home",
    load_intensity: "High",
  },
  // Tomorrow - Travel
  [formatDate(new Date(year, month, today.getDate() + 1))]: {
    date: formatDate(new Date(year, month, today.getDate() + 1)),
    is_traveling: true,
    location_type: "Remote",
    load_intensity: "Low",
  },
  // Day after tomorrow - Home
  [formatDate(new Date(year, month, today.getDate() + 2))]: {
    date: formatDate(new Date(year, month, today.getDate() + 2)),
    is_traveling: false,
    location_type: "Home",
    load_intensity: "Medium",
  },
}

export const mockScheduleState = {
  // Today - With backup activity (Bodyweight Flow instead of Heavy Lifting)
  [formatDate(today)]: ["act-1", "act-3", "act-5"],
  // Yesterday
  [formatDate(new Date(year, month, today.getDate() - 1))]: ["act-1", "act-2", "act-4"],
  // Tomorrow
  [formatDate(new Date(year, month, today.getDate() + 1))]: ["act-1", "act-5"],
  // Day after tomorrow
  [formatDate(new Date(year, month, today.getDate() + 2))]: ["act-1", "act-2", "act-4", "act-5"],
}

export const mockFailedActivities = {
  [formatDate(today)]: [
    {
      activity_name: "Heavy Weightlifting",
      reason: "User is traveling to Hotel/Resort (Remote Only)",
      priority: 2,
    },
  ],
}

// Helper function to format dates consistently
function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

export { formatDate }
