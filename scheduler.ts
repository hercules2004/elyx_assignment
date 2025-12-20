export type ActivityType = "Fitness" | "Food" | "Medication" | "Therapy" | "Consultation" | "Other";

export type Location = "Home" | "Gym" | "Clinic" | "Outdoors" | "Any";

export type FrequencyPattern = "Daily" | "Weekly" | "Monthly" | "Custom";

export interface Frequency {
  pattern: FrequencyPattern;
  count: number;
  preferred_days?: number[] | null;
  interval_days?: number | null;
}

export interface Activity {
  id: string;
  name: string;
  type: ActivityType;
  priority: number;
  frequency: Frequency;
  duration_minutes: number;
  preparation_duration_minutes: number;
  time_window_start?: string | null; // Format: "HH:MM:SS"
  time_window_end?: string | null;   // Format: "HH:MM:SS"
  specialist_id?: string | null;
  equipment_ids: string[];
  location: Location;
  remote_capable: boolean;
  details: string;
  preparation_requirements: string[];
  backup_activity_ids: string[];
  metrics_to_collect: string[];
}

export type SlotStatus = "Scheduled" | "Completed" | "Cancelled" | "Rescheduled";

export interface TimeSlot {
  activity_id: string;
  priority: number;
  date: string; // Format: "YYYY-MM-DD"
  start_time: string; // Format: "HH:MM:SS"
  duration_minutes: number;
  prep_duration_minutes: number;
  specialist_id?: string | null;
  equipment_ids: string[];
  is_backup: boolean;
  original_activity_id?: string | null;
  status: SlotStatus;
}

export interface DayContext {
  date: string;
  is_traveling: boolean;
  location_type: string;
  load_intensity: "Rest" | "Low" | "Medium" | "High";
}

export interface Failure {
  activity_id: string;
  reason: string;
  type: string;
}

export interface DashboardData {
  activities: Record<string, Activity>;
  schedule: Record<string, TimeSlot[]>;
  context: Record<string, DayContext>;
  failures: Record<string, Failure[]>;
}