"""
Schedule data models for the Adaptive Health Allocator.

This module defines the 'Output' of the scheduling engine:
Specific time slots where activities have been committed.
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import date as date_type, time as time_type, datetime, timedelta

class SlotStatus(str, Enum):
    """Status of the scheduled slot."""
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    RESCHEDULED = "Rescheduled"

class TimeSlot(BaseModel):
    """
    A committed block of time for a specific activity.
    Includes fields to track Resilience (Backups) and Prep Time.
    """

    # --- Core Scheduling Data ---
    activity_id: str = Field(description="ID of the activity effectively scheduled")
    date: date_type = Field(description="Calendar date")
    start_time: time_type = Field(description="Start time of the ACTIVITY ITSELF")
    duration_minutes: int = Field(ge=5, le=480, description="Duration of the activity")
    
    # Persist the prep time calculated during scheduling
    prep_duration_minutes: int = Field(
        default=0, 
        ge=0, 
        description="Minutes reserved immediately prior to start_time"
    )

    # --- Resource Allocation ---
    specialist_id: Optional[str] = Field(default=None, description="Assigned specialist")
    equipment_ids: List[str] = Field(default_factory=list, description="Assigned equipment")

    # --- Resilience Tracking (The 'Smart' Layer) ---
    is_backup: bool = Field(
        default=False, 
        description="True if this was scheduled as a fallback for another activity"
    )
    
    original_activity_id: Optional[str] = Field(
        default=None, 
        description="The ID of the Primary activity that failed (if is_backup=True)"
    )
    
    status: SlotStatus = Field(default=SlotStatus.SCHEDULED, description="Current state")

    @property
    def total_block_start(self) -> datetime:
        """Helper to get the actual start time including prep."""
        dt = datetime.combine(self.date, self.start_time)
        return dt - timedelta(minutes=self.prep_duration_minutes)

    @property
    def total_block_end(self) -> datetime:
        """Helper to get the actual end time."""
        dt = datetime.combine(self.date, self.start_time)
        return dt + timedelta(minutes=self.duration_minutes)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "activity_id": "act_home_workout_01",
            "date": "2025-01-15",
            "start_time": "07:30:00",
            "duration_minutes": 30,
            "prep_duration_minutes": 10,  # e.g., Set up mat
            "specialist_id": None,
            "equipment_ids": ["equip_mat_01"],
            "is_backup": True,
            "original_activity_id": "act_gym_class_01",
            "status": "Scheduled"
        }
    })