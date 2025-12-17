"""
Activity and Frequency data models for the Health Resource Allocator.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import time


class ActivityType(str, Enum):
    """Categorization of health activities."""
    FITNESS = "Fitness"
    FOOD = "Food"
    MEDICATION = "Medication"
    THERAPY = "Therapy"
    CONSULTATION = "Consultation"
    OTHER = "Other"


class Location(str, Enum):
    """Physical context where an activity can be performed."""
    HOME = "Home"
    GYM = "Gym"
    CLINIC = "Clinic"
    OUTDOORS = "Outdoors"
    ANY = "Any"


class FrequencyPattern(str, Enum):
    """Defines the recurrence pattern for an activity."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    CUSTOM = "Custom"


class Frequency(BaseModel):
    """Configuration for how often an activity should occur."""
    
    pattern: FrequencyPattern = Field(description="The recurrence pattern")
    count: int = Field(default=1, ge=1, description="Number of occurrences per period")
    
    preferred_days: Optional[List[int]] = Field(
        default=None,
        description="Specific days of the week (0=Monday, 6=Sunday). Only valid for Weekly pattern."
    )
    
    interval_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Day interval for Custom pattern (e.g., 2 for every other day)."
    )

    @field_validator('count')
    @classmethod
    def validate_count_limits(cls, v, info):
        """Ensure frequency counts are within logical bounds."""
        pattern = info.data.get('pattern')
        if pattern == FrequencyPattern.WEEKLY and v > 7:
            raise ValueError("Weekly frequency cannot exceed 7 days")
        if pattern == FrequencyPattern.MONTHLY and v > 31:
            raise ValueError("Monthly frequency cannot exceed 31 days")
        return v

    @model_validator(mode='after')
    def validate_configuration(self):
        """Ensure the frequency configuration is valid."""
        if self.pattern == FrequencyPattern.DAILY and self.preferred_days:
            raise ValueError("Daily pattern cannot specify preferred_days (implies all days)")
            
        if self.pattern == FrequencyPattern.CUSTOM and not self.interval_days:
            raise ValueError("Custom pattern requires 'interval_days' to be defined")
            
        return self


class Activity(BaseModel):
    """
    Represents a single health task to be scheduled.
    Includes timing, resource constraints, and resilience options.
    """

    # --- Core Identity ---
    id: str = Field(description="Unique identifier for the activity")
    name: str = Field(min_length=1, description="Human-readable name")
    type: ActivityType = Field(description="Category of the activity")
    priority: int = Field(ge=1, le=5, description="Priority level (1=Critical, 5=Optional)")
    
    # --- Timing & Frequency ---
    frequency: Frequency = Field(description="Schedule cadence configuration")
    duration_minutes: int = Field(ge=5, le=480, description="Duration of the activity itself")
    
    preparation_duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Time required immediately before the activity (e.g., travel, prep)"
    )

    # --- Time Windows ---
    time_window_start: Optional[time] = Field(
        default=None, 
        description="Earliest allowed start time"
    )
    time_window_end: Optional[time] = Field(
        default=None, 
        description="Latest allowed end time"
    )

    # --- Resource Constraints ---
    specialist_id: Optional[str] = Field(default=None, description="ID of required specialist")
    equipment_ids: List[str] = Field(default_factory=list, description="IDs of required equipment")
    location: Location = Field(default=Location.ANY, description="Required location context")
    
    remote_capable: bool = Field(
        default=False, 
        description="If True, activity can be performed remotely (e.g., during travel)"
    )

    # --- Metadata & Resilience ---
    details: str = Field(default="", description="User instructions or notes")
    
    preparation_requirements: List[str] = Field(
        default_factory=list,
        description="Description of preparation steps"
    )
    
    backup_activity_ids: List[str] = Field(
        default_factory=list,
        description="Ordered list of alternative Activity IDs to attempt if this activity fails to schedule"
    )
    
    metrics_to_collect: List[str] = Field(
        default_factory=list,
        description="List of metrics the user needs to record (e.g., 'HR', 'Weight')"
    )

    @model_validator(mode='after')
    def validate_time_window_logic(self):
        """Ensure start and end times form a valid window."""
        if (self.time_window_start and not self.time_window_end) or \
           (self.time_window_end and not self.time_window_start):
            raise ValueError("Both time_window_start and time_window_end must be provided together")
            
        if self.time_window_start and self.time_window_end:
            if self.time_window_end <= self.time_window_start:
                raise ValueError("Window end time must be after start time")
        return self

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "act_hbot_01",
            "name": "Hyperbaric Oxygen Therapy",
            "type": "Therapy",
            "priority": 2,
            "frequency": {"pattern": "Weekly", "count": 2},
            "duration_minutes": 60,
            "preparation_duration_minutes": 30,
            "time_window_start": "09:00:00",
            "time_window_end": "17:00:00",
            "specialist_id": "spec_tech_01",
            "equipment_ids": ["equip_chamber_01"],
            "location": "Clinic",
            "remote_capable": False,
            "backup_activity_ids": ["act_breathing_01"]
        }
    })