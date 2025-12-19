"""
Heuristic Scoring Engine for the Adaptive Health Allocator.

This module determines the 'Quality' of a valid time slot.
Unlike hard constraints (binary Yes/No), this provides a gradient (0.0 - 100.0)
to guide the scheduler toward "Human-Friendly" schedules.
"""

from datetime import date as date_type, time as time_type, datetime, timedelta
from typing import List, Dict
from collections import defaultdict

from models import Activity, TimeSlot

class SlotScorer:
    """
    Evaluates potential time slots based on soft constraints (User Preference, Efficiency, Resilience).
    """

    def __init__(self):
        self.daily_counts: Dict[date_type, int] = defaultdict(int)
        self.weekly_patterns: Dict[str, List[int]] = defaultdict(list)

    def calculate_score(
        self,
        activity: Activity,
        date: date_type,
        start_time: time_type,
        booked_slots: List[TimeSlot]
    ) -> float:
        """
        Master scoring function. Returns 0-100.
        """
        score = 50.0 # Base score

        # 1. Time Window Fidelity (+/- 20)
        # Does this slot sit nicely in the middle of the preferred window?
        score += self._score_time_window_fit(activity, start_time)

        # 2. Pattern Consistency (+/- 10)
        # Have we done this activity on this day before?
        score += self._score_consistency(activity, date)

        # 3. Clustering / Fragmentation (+/- 15)
        # Does this slot create a nice block of tasks, or scatter them?
        score += self._score_clustering(date, start_time, activity.duration_minutes, booked_slots)

        # 4. Resilience / Buffer (+/- 10)
        # Is there breathing room before/after this slot?
        score += self._score_buffer_zones(date, start_time, activity, booked_slots)

        # Clamp result
        return max(0.0, min(100.0, score))

    def _score_time_window_fit(self, activity: Activity, start_time: time_type) -> float:
        """
        Parabolic scoring to prefer the center of time windows.
        """
        if not (activity.time_window_start and activity.time_window_end):
            # General heuristic: People prefer 9am-5pm for "Work" type tasks,
            # and 6am-8am / 6pm-9pm for "Personal" type tasks.
            # For simplicity, we return neutral for now.
            return 0.0

        # Calculate minutes from midnight
        start_min = activity.time_window_start.hour * 60 + activity.time_window_start.minute
        end_min = activity.time_window_end.hour * 60 + activity.time_window_end.minute
        slot_min = start_time.hour * 60 + start_time.minute
        
        window_duration = end_min - start_min
        if window_duration <= 0: return 0.0

        # Normalize position 0.0 -> 1.0
        pos = (slot_min - start_min) / window_duration
        
        # Parabolic curve: Peak (1.0) at 0.5 (center), drops to 0.0 at edges
        # Formula: 1 - 4(x - 0.5)^2
        fit_quality = 1.0 - 4.0 * ((pos - 0.5) ** 2)
        
        return fit_quality * 20.0  # Max 20 points

    def _score_consistency(self, activity: Activity, date: date_type) -> float:
        """
        Reward repeating the same activity on the same day of the week.
        """
        weekday = date.weekday()
        history = self.weekly_patterns.get(activity.id, [])
        
        if not history: return 0.0
        
        count = history.count(weekday)
        if count > 2: return 10.0
        if count > 0: return 5.0
        return 0.0

    def _score_clustering(self, date: date_type, start: time_type, duration: int, slots: List[TimeSlot]) -> float:
        """
        Reward placing tasks back-to-back to preserve long blocks of free time.
        """
        day_slots = [s for s in slots if s.date == date]
        if not day_slots: return 0.0 # First task of the day

        slot_start_min = start.hour * 60 + start.minute
        slot_end_min = slot_start_min + duration

        # Check for adjacency
        for s in day_slots:
            s_start = s.start_time.hour * 60 + s.start_time.minute
            s_end = s_start + s.duration_minutes
            
            # Perfect adjacency (Task A ends exactly when Task B starts)
            if abs(s_end - slot_start_min) < 15 or abs(slot_end_min - s_start) < 15:
                return 15.0 # High reward for clustering

        return -5.0 # Slight penalty for "island" tasks

    def _score_buffer_zones(self, date: date_type, start: time_type, activity: Activity, slots: List[TimeSlot]) -> float:
        """
        Scores the resilience of the schedule based on gaps between tasks.
        
        Logic:
        - 0-15 mins gap:   Penalty (High risk of cascading delays).
        - 15-45 mins gap:  Reward (Ideal 'Goldilocks' buffer for travel/prep/rest).
        - 45-90 mins gap:  Neutral (Acceptable).
        - 90+ mins gap:    Small Penalty (Fragmentation/Dead time).
        """
        day_slots = [s for s in slots if s.date == date]
        if not day_slots:
            return 10.0  # First activity of the day is always resilient

        # Convert candidate start/end to minutes from midnight
        cand_start = start.hour * 60 + start.minute
        cand_end = cand_start + activity.duration_minutes + activity.preparation_duration_minutes

        # Find the gaps to the nearest neighbors
        gap_before = float('inf')
        gap_after = float('inf')

        for s in day_slots:
            # Existing slot times
            s_start = s.start_time.hour * 60 + s.start_time.minute
            s_end = s_start + s.duration_minutes + s.prep_duration_minutes

            # Check gap if 's' is before candidate
            if s_end <= cand_start:
                current_gap = cand_start - s_end
                if current_gap < gap_before:
                    gap_before = current_gap

            # Check gap if 's' is after candidate
            if cand_end <= s_start:
                current_gap = s_start - cand_end
                if current_gap < gap_after:
                    gap_after = current_gap

        # Evaluate the tightest constraint (usually the gap before)
        # We prioritize the 'gap_before' because that's where delays cascade from.
        relevant_gap = min(gap_before, gap_after)
        
        if relevant_gap == float('inf'):
            return 10.0 # No neighbors found (should be covered by empty check, but safe fallback)

        # --- SCORING LOGIC ---
        
        # DANGER ZONE (0-14 mins): High risk of overlap if previous task runs late
        if relevant_gap < 15:
            # Linear penalty: 0 min = -10 pts, 14 min = 0 pts
            return -10.0 + (relevant_gap / 1.5)

        # GOLDILOCKS ZONE (15-45 mins): Perfect buffer
        elif 15 <= relevant_gap <= 45:
            return 10.0 # Max reward

        # FRAGMENTATION ZONE (46-90 mins): Annoying dead time
        elif 46 <= relevant_gap <= 90:
            return 5.0 # Neutral/Okay

        # ISOLATION ZONE (> 90 mins): Good for deep work, but bad for "batching" health tasks
        else:
            return 0.0

    def record_booking(self, activity: Activity, slot: TimeSlot):
        """Update internal state after a successful booking."""
        self.daily_counts[slot.date] += 1
        self.weekly_patterns[activity.id].append(slot.date.weekday())