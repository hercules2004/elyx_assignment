"""
Resource and Constraint data models for the Adaptive Health Allocator.

This module defines the 'Supply' side of the scheduler:
1. Specialists (Human resources with shifts)
2. Equipment (Physical resources with maintenance)
3. Travel (Context that limits availability)
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import date, time


class SpecialistType(str, Enum):
    """Categories of human resources as defined in the assignment."""
    TRAINER = "Trainer"
    DIETITIAN = "Dietitian"
    THERAPIST = "Therapist"     # e.g., Mental health or Physio
    PHYSICIAN = "Physician"
    ALLIED_HEALTH = "Allied_Health" # e.g., Occupational Therapist


class AvailabilityBlock(BaseModel):
    """A specific time window when a resource is active."""
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time = Field(description="Shift start")
    end_time: time = Field(description="Shift end")

    @model_validator(mode='after')
    def validate_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("End time must be strictly after start time")
        return self


class Specialist(BaseModel):
    """
    Human resource with specific availability windows.
    """
    id: str = Field(description="Unique identifier")
    name: str = Field(min_length=1, description="Name of the professional")
    type: SpecialistType = Field(description="Role category")
    
    # Scheduling Constraints
    availability: List[AvailabilityBlock] = Field(
        description="Standard weekly operating hours"
    )
    days_off: List[date] = Field(
        default_factory=list, 
        description="Specific dates of unavailability (Holidays, Sick leave)"
    )
    
    # Capacity Constraint
    max_concurrent_clients: int = Field(
        default=1, 
        ge=1, 
        description="How many clients can be seen simultaneously"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "spec_physio_01",
            "name": "Sarah Jones",
            "type": "Allied_Health",
            "availability": [
                {"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"}
            ],
            "max_concurrent_clients": 1
        }
    })


class MaintenanceWindow(BaseModel):
    """Time range when a physical resource is broken or being serviced."""
    start_date: date
    end_date: date
    start_time: Optional[time] = Field(default=None, description="If None, applies to full day")
    end_time: Optional[time] = Field(default=None, description="If None, applies to full day")

    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Maintenance End Date cannot be before Start Date")
        return self


class Equipment(BaseModel):
    """
    Physical resource constraint.
    'is_portable' constraint to support travel logic.
    """
    id: str = Field(description="Unique identifier")
    name: str = Field(min_length=1, description="e.g. 'Hyperbaric Chamber'")
    location: str = Field(description="Physical location (matches Activity.Location logic)")
    
    # [SMART FEATURE]: If True, this constraint is satisfied even during travel
    is_portable: bool = Field(
        default=False, 
        description="Can the user take this with them? (e.g. Bands=True, Treadmill=False)"
    )

    maintenance_windows: List[MaintenanceWindow] = Field(
        default_factory=list,
        description="Periods of unavailability"
    )
    
    max_concurrent_users: int = Field(default=1, ge=1)
    requires_specialist: bool = Field(default=False, description="Does using this require supervision?")


class TravelPeriod(BaseModel):
    """
    Context modifier that overrides standard availability.
    'available_equipment_ids' constraint to allow gym use during travel.
    """
    id: str = Field(description="Unique identifier")
    start_date: date
    end_date: date
    location: str = Field(description="Destination name")
    
    # Logic Gate 1: Strict Remote Only
    remote_activities_only: bool = Field(
        default=False,
        description="If True, strictly forbids physical facility usage"
    )
    
    # Logic Gate 2: Available Resources (The 'Hotel Gym' Loophole)
    available_equipment_ids: List[str] = Field(
        default_factory=list,
        description="IDs of equipment available at the destination (e.g. Hotel Gym Treadmill)"
    )

    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Trip End Date cannot be before Start Date")
        return self