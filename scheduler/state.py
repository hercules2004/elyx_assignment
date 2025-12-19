"""
Scheduler State Management.

This module acts as the 'Memory' of the system.
It has been ENHANCED to track:
1. Standard Bookings & Resource Usage (from reference).
2. Resilience Metrics (Backup vs Primary usage).
3. Detailed Failure Reporting (for the final output).
"""

from datetime import date as date_type
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from models import Activity, TimeSlot
# We import ConstraintViolation to log specific failure reasons
from .constraints import ConstraintViolation


@dataclass
class SchedulingAttempt:
    """Record of failed scheduling attempts for an activity."""
    activity: Activity
    attempts: int = 0
    violations: List[ConstraintViolation] = field(default_factory=list)


class SchedulerState:
    """
    Maintains the mutable state of the scheduler during execution.
    Tracks bookings, resource consumption, and failure logs.
    """

    def __init__(self):
        """Initialize empty scheduler state."""
        # The Master Schedule
        self.booked_slots: List[TimeSlot] = []

        # Resource Indices (for O(1) constraints checking)
        self.specialist_bookings: Dict[str, List[TimeSlot]] = defaultdict(list)
        self.equipment_bookings: Dict[str, List[TimeSlot]] = defaultdict(list)
        
        # Activity Tracking
        self.activity_occurrences: Dict[str, int] = defaultdict(int)
        
        # Failure Tracking
        self.failed_activities: Dict[str, SchedulingAttempt] = {}

        # [NEW] Resilience Tracking
        # Maps original_activity_id -> List of Backup Slots booked in its place
        self.backup_activations: Dict[str, List[TimeSlot]] = defaultdict(list)

    def add_booking(self, slot: TimeSlot) -> None:
        """
        Commit a successful booking to the state.
        Updates all resource indices and counters.
        """
        self.booked_slots.append(slot)

        # 1. Track Specialist Usage
        if slot.specialist_id:
            self.specialist_bookings[slot.specialist_id].append(slot)

        # 2. Track Equipment Usage
        for equip_id in slot.equipment_ids:
            self.equipment_bookings[equip_id].append(slot)

        # 3. Track Occurrence Counts
        self.activity_occurrences[slot.activity_id] += 1

        # 4. [NEW] Track Resilience (Backup Usage)
        if slot.is_backup and slot.original_activity_id:
            self.backup_activations[slot.original_activity_id].append(slot)

    def record_failure(self, activity: Activity, violation: ConstraintViolation) -> None:
        """
        Log a failed attempt. 
        If an activity fails multiple times (e.g. checked 50 slots), we aggregate the reasons.
        """
        if activity.id not in self.failed_activities:
            self.failed_activities[activity.id] = SchedulingAttempt(
                activity=activity,
                attempts=1,
                violations=[violation]
            )
        else:
            attempt = self.failed_activities[activity.id]
            attempt.attempts += 1
            attempt.violations.append(violation)

    # --- Query Methods (Used by Constraints.py) ---

    def get_slots_for_date(self, date: date_type) -> List[TimeSlot]:
        """Get all bookings for a specific calendar date."""
        return [slot for slot in self.booked_slots if slot.date == date]

    def get_slots_for_activity(self, activity_id: str) -> List[TimeSlot]:
        """Get all scheduled instances of a specific activity."""
        return [slot for slot in self.booked_slots if slot.activity_id == activity_id]

    def get_occurrence_count(self, activity_id: str) -> int:
        """How many times has this activity been scheduled?"""
        return self.activity_occurrences[activity_id]

    def get_date_range(self) -> Optional[Tuple[date_type, date_type]]:
        """Return the start and end date of the current schedule."""
        if not self.booked_slots:
            return None
        dates = [slot.date for slot in self.booked_slots]
        return min(dates), max(dates)

    # --- Reporting Methods (Used by Output generators) ---

    def get_statistics(self) -> Dict[str, Any]:
        """
        Generate comprehensive stats for the final report.
        ENHANCED to include Resilience Metrics.
        """
        if not self.booked_slots:
            return {
                "total_slots": 0,
                "unique_activities": 0,
                "failed_count": len(self.failed_activities),
                "resilience_score": 0.0
            }

        dates = [slot.date for slot in self.booked_slots]
        date_counts = defaultdict(int)
        for d in dates:
            date_counts[d] += 1
            
        busiest_day = max(date_counts.items(), key=lambda x: x[1]) if date_counts else None
        
        # Calculate Resilience Score
        total_bookings = len(self.booked_slots)
        backup_bookings = sum(1 for s in self.booked_slots if s.is_backup)
        primary_bookings = total_bookings - backup_bookings
        
        # Percentage of plan that is "Ideal" (Primary) vs "Adaptive" (Backup)
        resilience_rate = (backup_bookings / total_bookings) * 100 if total_bookings else 0

        # --- Priority Breakdown Analysis ---
        # Structure: { 1: {'success': X, 'failed': Y, 'total': Z}, ... }
        priority_stats = defaultdict(lambda: {"success": 0, "failed": 0, "total": 0})

        # 1. Count Successes (from Booked Slots)
        for slot in self.booked_slots:
            p = slot.priority
            priority_stats[p]["success"] += 1
            priority_stats[p]["total"] += 1

        # 2. Count Failures (from Failed Attempts)
        # We count "Exhaustion" violations, which represent a completely dropped occurrence.
        for attempt in self.failed_activities.values():
            p = attempt.activity.priority
            exhaustion_count = sum(1 for v in attempt.violations if v.constraint_type == "Exhaustion")
            priority_stats[p]["failed"] += exhaustion_count
            priority_stats[p]["total"] += exhaustion_count

        # 3. Format Breakdown
        breakdown = {}
        for p in sorted(priority_stats.keys()):
            s = priority_stats[p]
            rate = (s["success"] / s["total"] * 100) if s["total"] > 0 else 0.0
            breakdown[f"P{p}"] = f"{rate:.1f}% ({s['success']}/{s['total']})"

        total_demand = sum(s['total'] for s in priority_stats.values())
        overall_success = (total_bookings / total_demand * 100) if total_demand > 0 else 0.0

        return {
            "total_slots": total_bookings,
            "primary_slots": primary_bookings,
            "backup_slots": backup_bookings,
            "resilience_rate": round(resilience_rate, 1),
            
            "unique_activities": len(self.activity_occurrences),
            "overall_success_rate": f"{overall_success:.1f}%",
            "priority_breakdown": breakdown,
            
            "date_range": (min(dates), max(dates)),
            "busiest_day": busiest_day,
            
            "specialist_usage_count": {k: len(v) for k, v in self.specialist_bookings.items()},
            "equipment_usage_count": {k: len(v) for k, v in self.equipment_bookings.items()},
            
            # Only count activities that had a Terminal Failure (Exhaustion)
            "failed_activities_count": sum(1 for a in self.failed_activities.values() if any(v.constraint_type == "Exhaustion" for v in a.violations))
        }

    def get_failure_report(self) -> List[Dict]:
        """
        Generate a human-readable list of what failed and why.
        Useful for the 'Missed Opportunities' section of the output.
        """
        report = []

        for activity_id, attempt in self.failed_activities.items():
            # [FILTER] Only report 'Terminal Failures' (Exhaustion).
            # If an activity failed initially but was saved by a Backup, 
            # it will NOT have an 'Exhaustion' error. We skip those to reduce noise.
            if not any(v.constraint_type == "Exhaustion" for v in attempt.violations):
                continue

            # Aggregate violation reasons (e.g. "Specialist Busy: 50 times")
            violation_summary = defaultdict(int)
            for v in attempt.violations:
                violation_summary[v.constraint_type] += 1

            # Get the most common specific reason text
            sample_reason = "Unknown"
            if attempt.violations:
                sample_reason = attempt.violations[0].reason

            report.append({
                "activity_id": activity_id,
                "activity_name": attempt.activity.name,
                "priority": attempt.activity.priority,
                "total_attempts": attempt.attempts,
                "primary_failure_cause": max(violation_summary, key=violation_summary.get),
                "violation_breakdown": dict(violation_summary),
                "latest_reason": sample_reason
            })

        # Sort failures by Priority (Critical failures first)
        report.sort(key=lambda x: x["priority"])
        return report

    def clear(self) -> None:
        """Reset state (useful for testing or re-running phases)."""
        self.booked_slots.clear()
        self.specialist_bookings.clear()
        self.equipment_bookings.clear()
        self.activity_occurrences.clear()
        self.failed_activities.clear()
        self.backup_activations.clear()