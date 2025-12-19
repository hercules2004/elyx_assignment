"""
The Adaptive Health Scheduling Engine.

This module implements the core "Solver" logic.
It combines three powerful strategies:
1. Heuristic Scoring (Most Constrained First) - Solves the "Tetris" problem.
2. Capacity Quotas (Balanced Logic) - Prevents burnout / dominance of single task types.
3. Resilience Loops (Fallback Chains) - Solves the "Real World" problem of unavailable resources.
"""

import datetime
import logging
from datetime import date as date_type, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from models import Activity, Specialist, Equipment, TravelPeriod, TimeSlot, FrequencyPattern
from .constraints import ConstraintChecker, ConstraintViolation
from .scoring import SlotScorer
from .state import SchedulerState

logger = logging.getLogger(__name__)

class AdaptiveScheduler:
    """
    Main scheduling engine.
    Ingests Demand (Activities) and Supply (Resources), outputs a Schedule.
    """

    # Soft Limits: Prevent any single Priority tier from monopolizing the day
    PRIORITY_QUOTAS = {
        1: 1.00, # Critical tasks can take 100% of day
        2: 0.80,
        3: 0.60,
        4: 0.50,
        5: 0.40
    }
    MAX_DAILY_SLOTS = 10 # Reduced to ~5-6 hours of active health time per day

    def __init__(
        self,
        activities: List[Activity],
        specialists: List[Specialist],
        equipment: List[Equipment],
        travel_periods: List[TravelPeriod],
        start_date: date_type,
        duration_days: int = 90,
        backup_lookup: Optional[Dict[str, Activity]] = None
    ):
        self.activities = activities
        self.start_date = start_date
        self.duration_days = duration_days
        self.end_date = start_date + timedelta(days=duration_days - 1)

        # Initialize Helpers
        self.checker = ConstraintChecker(specialists, equipment, travel_periods)
        self.scorer = SlotScorer()
        self.state = SchedulerState()
        
        # Lookups
        self.activity_map = {a.id: a for a in activities}
        if backup_lookup:
            self.activity_map.update(backup_lookup)
        self.daily_load: Dict[date_type, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

    def run(self) -> SchedulerState:
        """
        Execute the scheduling pipeline.
        """
        logger.info("Starting Adaptive Scheduler...")

        # 1. Expand Demand: Convert "3x/week" into specific "ActivityOccurrence" objects
        # We need to know EXACTLY how many slots we are trying to fill.
        occurrences = self._expand_occurrences()
        
        # 2. Sort by "Difficulty" (Heuristic)
        # We process the HARDEST constraints first (e.g. Specialists, Tight Windows)
        occurrences.sort(key=lambda x: x['difficulty_score'], reverse=True)

        # 3. Main Loop: Try to place each occurrence
        for occ in occurrences:
            activity = occ['activity']
            
            # Attempt 1: Primary Activity (Preferred Days)
            success = self._attempt_placement(activity, occ['index_in_sequence'], scope="narrow")
            
            # Attempt 2: Fallback Chain (Resilience Logic - Preferred Days)
            if not success and activity.backup_activity_ids:
                success = self._attempt_fallback_chain(activity, occ['index_in_sequence'], scope="narrow")

            # Attempt 3: Liquid Scheduling (Primary Activity - Any Day in Week)
            # If rigid slots failed, try to fit the Primary anywhere in the week to meet quota.
            if not success and activity.frequency.pattern in [FrequencyPattern.WEEKLY, FrequencyPattern.MONTHLY]:
                success = self._attempt_placement(activity, occ['index_in_sequence'], scope="wide")

            if not success:
                # Log final failure after all retries
                self.state.record_failure(activity, ConstraintViolation(
                    constraint_type="Exhaustion",
                    reason="All placement attempts failed",
                    activity_id=activity.id,
                    date=self.start_date,
                    start_time=datetime.time(0, 0)
                ))

        return self.state

    def _attempt_placement(self, activity: Activity, occ_index: int, is_backup: bool = False, original_id: str = None, scope: str = "narrow") -> bool:
        """
        Tries to find a valid slot for a specific activity instance.
        """
        # 1. Generate Candidates (Days/Times)
        candidates = self._generate_candidates(activity, occ_index, scope)
        
        valid_slots = []
        for date, time in candidates:
            # A. Check Quota (Skip if day is too full of this priority type)
            # Note: We skip quota checks for Backups (they are last resort)
            if not is_backup and not self._check_quota(date, activity.priority):
                continue
            
            # B. Check Hard Constraints
            violation = self.checker.check_time_slot(activity, date, time, self.state.booked_slots, is_backup=is_backup)
            
            if violation is None:
                # C. Score Soft Constraints
                score = self.scorer.calculate_score(activity, date, time, self.state.booked_slots)
                valid_slots.append((score, date, time))
            else:
                # Only record failure if it's the Primary activity (to avoid log noise)
                if not is_backup:
                    self.state.record_failure(activity, violation)

        if not valid_slots:
            return False

        # 2. Pick Winner
        valid_slots.sort(key=lambda x: x[0], reverse=True)
        best_score, best_date, best_time = valid_slots[0]

        # 3. Commit
        slot = TimeSlot(
            activity_id=activity.id,
            priority=activity.priority,
            date=best_date,
            start_time=best_time,
            duration_minutes=activity.duration_minutes,
            prep_duration_minutes=activity.preparation_duration_minutes,
            specialist_id=activity.specialist_id,
            equipment_ids=activity.equipment_ids,
            is_backup=is_backup,
            original_activity_id=original_id
        )
        self.state.add_booking(slot)
        self.scorer.record_booking(activity, slot)
        
        # Update Load
        self.daily_load[best_date][activity.priority] += 1
        
        return True

    def _attempt_fallback_chain(self, primary_activity: Activity, occ_index: int, scope: str = "narrow") -> bool:
        """
        Iterates through the backup_activity_ids list.
        Returns True if ANY backup is successfully scheduled.
        """
        for backup_id in primary_activity.backup_activity_ids:
            backup_act = self.activity_map.get(backup_id)
            if not backup_act:
                logger.warning(f"Backup ID {backup_id} not found in activity list.")
                continue
                
            logger.info(f"Triggering Fallback: {primary_activity.name} -> {backup_act.name}")
            
            # We try to schedule the backup roughly where the primary would have gone
            if self._attempt_placement(backup_act, occ_index, is_backup=True, original_id=primary_activity.id, scope=scope):
                return True
                
        return False

    def _check_quota(self, date: date_type, priority: int) -> bool:
        """Balanced Logic: Ensure diversity of tasks."""
        current = self.daily_load[date][priority]
        limit = self.MAX_DAILY_SLOTS * self.PRIORITY_QUOTAS.get(priority, 0.1)
        return current < limit

    def _expand_occurrences(self) -> List[Dict]:
        """
        Flattens the frequency patterns into a single list of 'Tasks to Schedule'.
        Calculates a 'Difficulty Score' for each to drive the sorting order.
        """
        tasks = []
        for activity in self.activities:
            count = self._calculate_required_count(activity)
            
            # Heuristic Score:
            # Base: Priority (inverted) * 100
            # + Specialist (50)
            # + Equipment (30)
            # + Tight Window (40)
            score = (6 - activity.priority) * 100
            if activity.specialist_id: score += 50
            if activity.equipment_ids: score += 30 * len(activity.equipment_ids)
            if activity.time_window_start: score += 40
            
            for i in range(count):
                tasks.append({
                    'activity': activity,
                    'index_in_sequence': i,
                    'difficulty_score': score
                })
        return tasks

    def _calculate_required_count(self, activity: Activity) -> int:
        """(Same logic as reference, just helper for expansion)"""
        f = activity.frequency
        if f.pattern == FrequencyPattern.DAILY: return self.duration_days
        if f.pattern == FrequencyPattern.WEEKLY: return (self.duration_days // 7) * f.count
        if f.pattern == FrequencyPattern.MONTHLY: return (self.duration_days // 30) * f.count
        if f.pattern == FrequencyPattern.CUSTOM: return self.duration_days // (f.interval_days or 1)
        return 0

    def _generate_candidates(self, activity: Activity, index: int, scope: str = "narrow") -> List[Tuple[date_type, object]]:
        """
        Generates candidate slots (Date, Time) for a specific occurrence of an activity.
        
        Logic:
        1. Calculate the 'Ideal Date' based on the frequency pattern.
        2. Generate 'Primary' candidates on that ideal date.
        3. Generate 'Backup' candidates on surrounding days (to allow flexibility).
        """
        freq = activity.frequency
        candidates = []

        # LIQUID SCHEDULING: Wide Scope
        if scope == "wide":
            if freq.pattern == FrequencyPattern.WEEKLY:
                week_num = index // freq.count
                # Start of the 7-day block
                week_start = self.start_date + timedelta(weeks=week_num)
                
                # Try all 7 days in the block
                for d in range(7):
                    day = week_start + timedelta(days=d)
                    if self.start_date <= day <= self.end_date:
                        candidates.extend(self._generate_times_for_date(activity, day))
                return candidates
            
            elif freq.pattern == FrequencyPattern.MONTHLY:
                # Monthly Liquid: Try a 7-day window starting from the target date
                # This prevents "1st of the month" congestion from killing the task
                month_num = index // freq.count
                base_date = self.start_date + timedelta(days=30 * month_num)
                
                for d in range(7):
                    day = base_date + timedelta(days=d)
                    if self.start_date <= day <= self.end_date:
                        candidates.extend(self._generate_times_for_date(activity, day))
                return candidates
        
        # --- Step 1: Identify the Target Date ---
        target_date = None

        if freq.pattern == FrequencyPattern.DAILY:
            # Simple: Day 0 + Index
            target_date = self.start_date + timedelta(days=index)

        elif freq.pattern == FrequencyPattern.WEEKLY:
            # Week calculation
            week_num = index // freq.count
            occurrence_in_week = index % freq.count
            
            # Determine target weekday (0=Mon, 6=Sun)
            if freq.preferred_days:
                # Cycle through preferred days
                weekday = freq.preferred_days[occurrence_in_week % len(freq.preferred_days)]
            else:
                # Default spread: Mon, Wed, Fri, etc.
                weekday = (occurrence_in_week * 2) % 7 
            
            # Find the actual date
            week_start = self.start_date + timedelta(weeks=week_num)
            # Adjust week_start to be the Monday of that week if needed, 
            # but here we assume start_date is the anchor.
            # Let's find the specific weekday relative to week_start
            days_offset = (weekday - week_start.weekday() + 7) % 7
            target_date = week_start + timedelta(days=days_offset)

        elif freq.pattern == FrequencyPattern.MONTHLY:
            # Month calculation
            month_num = index // freq.count
            # Rough approximation: 30 days per month
            target_date = self.start_date + timedelta(days=30 * month_num)
            
        elif freq.pattern == FrequencyPattern.CUSTOM:
            interval = freq.interval_days or 1
            target_date = self.start_date + timedelta(days=index * interval)

        # --- Step 2: Generate Slots for Target Date ---
        if target_date and self.start_date <= target_date <= self.end_date:
            candidates.extend(self._generate_times_for_date(activity, target_date))

        # --- Step 3: Add Flexibility (Backup Days) ---
        # If it's not a Daily task (which is rigid), check neighbors
        if freq.pattern != FrequencyPattern.DAILY and target_date:
            # Try 1 day before
            prev_date = target_date - timedelta(days=1)
            if prev_date >= self.start_date:
                candidates.extend(self._generate_times_for_date(activity, prev_date))
            
            # Try 1 day after
            next_date = target_date + timedelta(days=1)
            if next_date <= self.end_date:
                candidates.extend(self._generate_times_for_date(activity, next_date))

        return candidates

    def _generate_times_for_date(self, activity: Activity, date: date_type) -> List[Tuple[date_type, object]]:
        """
        Helper: Returns specific time options for a single date.
        Respects Time Windows if they exist, otherwise tries Morning/Afternoon/Evening.
        """
        times = []
        
        # Case A: Strict Time Window (e.g., "08:00 to 10:00")
        if activity.time_window_start and activity.time_window_end:
            start_h = activity.time_window_start.hour
            end_h = activity.time_window_end.hour
            
            # Generate slots every 30 mins within window
            for h in range(start_h, end_h + 1):
                for m in [0, 30]:
                    t = timedelta(hours=h, minutes=m)
                    # Convert back to time object
                    candidate_time = (datetime.datetime.min + t).time()
                    
                    # Validate fit
                    if candidate_time >= activity.time_window_start:
                        # Check if Duration fits before Window End
                        end_min = h * 60 + m + activity.duration_minutes
                        window_end_min = activity.time_window_end.hour * 60 + activity.time_window_end.minute
                        
                        if end_min <= window_end_min:
                            times.append((date, candidate_time))

        # Case B: Open Schedule (Try standard "Reasonable" hours)
        else:
            # We assume reasonable hours are 7 AM to 8 PM
            # We try 3 slots per day to keep search space manageable
            standard_options = [
                (7, 0),   # Early Morning
                (9, 0),   # Start of Work
                (12, 0),  # Lunch
                (17, 0),  # After Work
                (19, 0),  # Evening
                (22,0) # Post-Dinner
            ]
            
            for h, m in standard_options:
                t = timedelta(hours=h, minutes=m)
                times.append((date, (datetime.datetime.min + t).time()))

        return times