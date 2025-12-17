"""
Data models package for the Adaptive Health Allocator.

This package exports the three core pillars of the data architecture:
1. Demand (Activity, Frequency)
2. Supply (Specialist, Equipment, Travel)
3. Output (TimeSlot, SlotStatus)
"""

from .activity import (
    Activity,
    ActivityType,
    Frequency,
    FrequencyPattern,
    Location
)

from .resource import (
    Specialist,
    SpecialistType,
    AvailabilityBlock,
    Equipment,
    MaintenanceWindow,
    TravelPeriod
)

from .schedule import (
    TimeSlot,
    SlotStatus
)

__all__ = [
    # --- Demand Models ---
    "Activity",
    "ActivityType",
    "Frequency",
    "FrequencyPattern",
    "Location",

    # --- Resource & Constraint Models ---
    "Specialist",
    "SpecialistType",
    "AvailabilityBlock",
    "Equipment",
    "MaintenanceWindow",
    "TravelPeriod",

    # --- Output Models ---
    "TimeSlot",
    "SlotStatus",
]