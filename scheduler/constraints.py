"""
Hard Constraint Validation Logic.

This module answers the binary question: "Can Activity X happen at Time Y?"
It enforces physical reality (two things can't happen at once) and resource limits.
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot

@dataclass
class ConstraintViolation:
    """Detailed reason for rejection."""
    constraint_type: str  # e.g., "Overlap", "Resource", "Travel"
    reason: str
    activity_id: str
    date: date_type
    start_time: time_type

class ConstraintChecker:
    """
    Validates hard constraints for activity scheduling.
    """

    def __init__(
        self,
        specialists: List[Specialist],
        equipment: List[Equipment],
        travel_periods: List[TravelPeriod]
    ):
        # Index resources for O(1) lookup
        self.specialists = {s.id: s for s in specialists}
        self.equipment = {e.id: e for e in equipment}
        self.travel_periods = travel_periods

    def check_time_slot(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot],
        is_backup: bool = False
    ) -> Optional[ConstraintViolation]:
        """
        Master validation function. Returns None if Valid, Violation object if Invalid.
        """
        
        # 1. Check Travel Context (Highest Priority - filters out impossible contexts)
        violation = self._check_travel_context(activity, date, is_backup)
        if violation: return violation

        # 2. Check Resource Availability (Specialist / Equipment)
        if activity.specialist_id:
            violation = self._check_specialist(activity, date, start_time)
            if violation: return violation

        if activity.equipment_ids:
            # Note: We pass the travel context to equipment check to handle "Hotel Gyms"
            is_traveling = self._get_active_travel(date) is not None
            violation = self._check_equipment(activity, date, start_time, booked_slots, is_traveling)
            if violation: return violation

        # 3. Check Time Conflicts (Overlap & Window)
        # [CRITICAL UPGRADE]: We account for Prep Time here
        violation = self._check_overlap(activity, date, start_time, booked_slots)
        if violation: return violation

        if activity.time_window_start and activity.time_window_end:
            violation = self._check_time_window(activity, date, start_time)
            if violation: return violation

        return None # All clear!

    def _check_overlap(self, activity: Activity, date: date_type, start: time_type, slots: List[TimeSlot]) -> Optional[ConstraintViolation]:
        """
        Ensures the new activity (plus its prep time!) doesn't clash with existing slots.
        """
        # Calculate the FULL block (Prep + Activity)
        # We model prep time as happening *immediately before* the start time.
        # But for overlap, we just need to ensure the whole block [Start-Prep, Start+Duration] is free.
        
        # Simpler approach: We treat the slot as starting at (Start - Prep)
        # But existing logic usually keys off 'start_time'. 
        # Let's check overlap for the activity itself AND the prep block.
        
        act_start_min = start.hour * 60 + start.minute
        act_end_min = act_start_min + activity.duration_minutes
        
        # Prep block is [Start - Prep, Start]
        prep_start_min = act_start_min - activity.preparation_duration_minutes
        
        # Effective range to check: [Prep_Start, Activity_End]
        check_start = prep_start_min
        check_end = act_end_min

        for slot in slots:
            if slot.date != date: continue
            
            # Existing slot range (including its own prep!)
            s_start = slot.start_time.hour * 60 + slot.start_time.minute
            s_prep = slot.prep_duration_minutes
            s_dur = slot.duration_minutes
            
            s_range_start = s_start - s_prep
            s_range_end = s_start + s_dur
            
            # Standard Overlap Logic: StartA < EndB and StartB < EndA
            if check_start < s_range_end and s_range_start < check_end:
                return ConstraintViolation(
                    "Overlap", 
                    f"Clash with {slot.activity_id} (incl. prep time)", 
                    activity.id, date, start
                )
        return None

    def _check_travel_context(self, activity: Activity, date: date_type, is_backup: bool) -> Optional[ConstraintViolation]:
        """
        Enforces constraints when the user is away from home.
        """
        active_trip = self._get_active_travel(date)
        if not active_trip:
            return None

        # --- THE FIX: IMMUNITY FOR BACKUPS ---
        # If this is a Backup activity, we assume it is designed to be performed 
        # anywhere (Hotel room, Cabin, etc.), so we BYPASS location checks.
        if is_backup:
            return None

        # [LOGIC FIX]: Determine if activity is "Effectively Remote" (All equipment is portable)
        # This teaches the engine that Portable Equipment travels with the user.
        is_effectively_remote = activity.remote_capable
        
        if not is_effectively_remote:
            # Check if all required equipment is portable
            all_portable = True
            if activity.equipment_ids:
                for eq_id in activity.equipment_ids:
                    equip = self.equipment.get(eq_id)
                    # If equipment missing or not portable, then it's not portable
                    if not equip or not equip.is_portable:
                        all_portable = False
                        break
            if all_portable:
                is_effectively_remote = True

        # Rule 1: If strictly remote-only (e.g. Hiking), reject non-remote tasks.
        if active_trip.remote_activities_only and not is_effectively_remote:
            return ConstraintViolation(
                "Travel", 
                f"User is traveling to {active_trip.location} (Remote Only)", 
                activity.id, date, time_type(0,0)
            )

        # Rule 2: If trip allows facilities (Hotel), we check equipment availability in _check_equipment
        # But if the activity requires a SPECIFIC LOCATION (e.g. "Home"), fail it.
        # Exception: If it's effectively remote (portable), we allow "Home" tasks during travel.
        if activity.location == "Home" and not is_effectively_remote:
             return ConstraintViolation(
                "Travel", 
                f"User is away at {active_trip.location}, cannot do Home activity", 
                activity.id, date, time_type(0,0)
            )
        
        return None

    def _check_equipment(self, activity: Activity, date: date_type, start: time_type, slots: List[TimeSlot], is_traveling: bool) -> Optional[ConstraintViolation]:
        """
        Checks equipment access, handling the 'Portable' and 'Hotel Gym' exceptions.
        """
        active_trip = self._get_active_travel(date)
        
        for eq_id in activity.equipment_ids:
            equip = self.equipment.get(eq_id)
            if not equip: continue # Should log warning, but skip for now

            # Logic: If traveling, is the equipment available THERE?
            if is_traveling:
                # 1. Is it portable? (Yoga Mat) -> OK
                if equip.is_portable:
                    pass 
                # 2. Is it provided by the destination? (Hotel Treadmill) -> OK
                elif active_trip and eq_id in active_trip.available_equipment_ids:
                    pass
                # 3. Otherwise -> FAIL
                else:
                    return ConstraintViolation(
                        "Equipment",
                        f"Equipment {equip.name} not available during travel to {active_trip.location}",
                        activity.id, date, start
                    )

            # Logic: Maintenance Check (Applies everywhere)
            for window in equip.maintenance_windows:
                if window.start_date <= date <= window.end_date:
                    # Simple day-level check for now
                    return ConstraintViolation(
                        "Equipment",
                        f"{equip.name} is under maintenance",
                        activity.id, date, start
                    )

            # Logic: Concurrency Check (Max Users)
            # (Simplified: count slots using this equipment at this time)
            usage_count = 0
            act_start = start.hour * 60 + start.minute
            act_end = act_start + activity.duration_minutes
            
            for s in slots:
                if s.date == date and eq_id in s.equipment_ids:
                    s_start = s.start_time.hour * 60 + s.start_time.minute
                    s_end = s_start + s.duration_minutes
                    if act_start < s_end and s_start < act_end:
                        usage_count += 1
            
            if usage_count >= equip.max_concurrent_users:
                 return ConstraintViolation("Equipment", f"{equip.name} is full", activity.id, date, start)

        return None

    def _check_specialist(self, activity: Activity, date: date_type, start: time_type) -> Optional[ConstraintViolation]:
        """Standard check for specialist working hours."""
        spec = self.specialists.get(activity.specialist_id)
        if not spec: return None

        if date in spec.days_off:
            return ConstraintViolation("Specialist", f"{spec.name} is off today", activity.id, date, start)

        # Check Shifts
        day_idx = date.weekday()
        shifts = [b for b in spec.availability if b.day_of_week == day_idx]
        
        is_covered = False
        act_end_min = start.hour * 60 + start.minute + activity.duration_minutes
        
        for shift in shifts:
            shift_start_min = shift.start_time.hour * 60 + shift.start_time.minute
            shift_end_min = shift.end_time.hour * 60 + shift.end_time.minute
            
            # Activity must fit ENTIRELY within shift
            if (start.hour*60 + start.minute) >= shift_start_min and act_end_min <= shift_end_min:
                is_covered = True
                break
        
        if not is_covered:
            return ConstraintViolation("Specialist", f"{spec.name} is not working at this time", activity.id, date, start)
            
        return None

    def _check_time_window(self, activity: Activity, date: date_type, start: time_type) -> Optional[ConstraintViolation]:
        """Basic check if activity fits in its preferred window."""
        if start < activity.time_window_start:
             return ConstraintViolation("TimeWindow", "Too early", activity.id, date, start)
        
        # End time check
        end_min = start.hour*60 + start.minute + activity.duration_minutes
        win_end_min = activity.time_window_end.hour*60 + activity.time_window_end.minute
        
        if end_min > win_end_min:
            return ConstraintViolation("TimeWindow", "Too late", activity.id, date, start)
        return None

    def _get_active_travel(self, date: date_type) -> Optional[TravelPeriod]:
        """Helper to find if a date falls inside any travel period."""
        for travel in self.travel_periods:
            if travel.start_date <= date <= travel.end_date:
                return travel
        return None