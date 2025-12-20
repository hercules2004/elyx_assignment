"""
Main Execution Script for the Adaptive Health Allocator.
UPDATED: Fixes "Primary vs Backup Clash" by segregating lists before scheduling.
"""

import os
import sys
import logging
from datetime import date, timedelta
import json

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generators.data_factory import DataGenerator
from scheduler.engine import AdaptiveScheduler
from models import Activity, Specialist, Equipment, TravelPeriod

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Main")

# --- CONFIGURATION ---
CACHE_FILENAME = "debug_data.json"
USE_CACHE = True # Set to False to force new AI generation
# ---------------------

def save_debug_data(data: dict, filename: str):
    """Helper to save generated data so we don't re-query LLM every time."""
    serializable = {}
    for key, val in data.items():
        if isinstance(val, list):
            serializable[key] = [item.model_dump(mode='json') for item in val]
    
    with open(filename, 'w') as f:
        json.dump(serializable, f, indent=2)
    logger.info(f"💾 Saved debug data to {filename}")

def load_cached_data(filename: str):
    """
    Helper to load JSON data and reconstruct Pydantic objects.
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            
        logger.info(f"📂 Loading cached data from {filename}...")
        
        # Re-hydrate Pydantic models from the JSON dicts
        activities = [Activity(**item) for item in data.get('activities', [])]
        specialists = [Specialist(**item) for item in data.get('specialists', [])]
        equipment = [Equipment(**item) for item in data.get('equipment', [])]
        travel = [TravelPeriod(**item) for item in data.get('travel', [])]
        
        resources = {
            "specialists": specialists,
            "equipment": equipment,
            "travel": travel
        }
        
        logger.info(f"✅ Cache Loaded: {len(activities)} activities, {len(specialists)} specialists.")
        return activities, resources

    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"⚠️ Cache file {filename} not found or invalid. Falling back to Generator.")
        return None, None
    except Exception as e:
        logger.error(f"❌ Failed to load cache: {e}")
        return None, None

def export_dashboard_data(state, activities_map, travel_periods, filename="dashboard_data.json"):
    """
    Serializes the scheduler state into a JSON format for the frontend.
    """
    logger.info(f"💾 Exporting dashboard data to {filename}...")
    
    data = {
        "activities": {},
        "schedule": {},
        "context": {},
        "failures": {}
    }

    # 1. Activities Map
    for aid, act in activities_map.items():
        data["activities"][aid] = act.model_dump(mode='json')

    # 2. Schedule (Grouped by Date)
    for slot in state.booked_slots:
        date_key = slot.date.isoformat()
        if date_key not in data["schedule"]:
            data["schedule"][date_key] = []
        data["schedule"][date_key].append(slot.model_dump(mode='json'))

    # 3. Context (Travel & Load)
    if state.booked_slots:
        dates = sorted(list(set(s.date for s in state.booked_slots)))
        start_date = dates[0]
        end_date = dates[-1]
        
        current = start_date
        while current <= end_date:
            date_key = current.isoformat()
            
            # Context: Travel
            is_traveling = False
            location = "Home"
            for trip in travel_periods:
                if trip.start_date <= current <= trip.end_date:
                    is_traveling = True
                    location = trip.location
                    break
            
            # Context: Load
            day_slots = [s for s in state.booked_slots if s.date == current]
            count = len(day_slots)
            if count == 0: load = "Rest"
            elif count <= 3: load = "Low"
            elif count <= 6: load = "Medium"
            else: load = "High"

            data["context"][date_key] = {
                "date": date_key,
                "is_traveling": is_traveling,
                "location_type": location,
                "load_intensity": load
            }
            
            current += timedelta(days=1)

    # 4. Failures (Grouped by Date)
    for aid, attempt in state.failed_activities.items():
        for v in attempt.violations:
            d_key = v.date.isoformat()
            if d_key not in data["failures"]:
                data["failures"][d_key] = []
            
            data["failures"][d_key].append({
                "activity_id": aid,
                "reason": v.reason,
                "type": v.constraint_type
            })

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info("✅ Dashboard data exported.")

def main():
    if not API_KEY and not USE_CACHE:
        logger.error("❌ GOOGLE_API_KEY not found. Please set it via 'export GOOGLE_API_KEY=...'")
        return

    logger.info("🚀 Starting Adaptive Health Allocator Integration Test...")
    start_date = date.today()
    
    # Placeholders
    activities = []
    resources = {}

    # --- PHASE 1: DATA ACQUISITION (Cache vs. GenAI) ---
    if USE_CACHE:
        activities, resources = load_cached_data(CACHE_FILENAME)

    if not activities:
        generator = DataGenerator(api_key=API_KEY)
        logger.info("--- Phase 1: Generative AI Data Fetch ---")
        
        # A. Activities (Returns BOTH Primaries and Backups)
        activities, cost_act = generator.generate_resilient_activities(count=30, start_date=start_date)
        
        # B. Resources
        resources, cost_res = generator.generate_resources(
            specialist_count=5, 
            equipment_count=5, 
            travel_count=2,
            start_date=start_date
        )
        
        logger.info(f"💸 Total Estimated LLM Cost: ${cost_act + cost_res:.4f}")
        
        # Save to Cache
        save_debug_data({
            "activities": activities,
            **resources
        }, CACHE_FILENAME)

    # --- PHASE 2: ADAPTIVE SCHEDULING ---
    if not activities:
        logger.error("❌ No data available. Exiting.")
        return

    logger.info("\n--- Phase 2: Adaptive Scheduling Engine ---")
    
    # 🔥 CRITICAL FIX: SEGREGATE THE LISTS 🔥
    # Only Primaries go into the main scheduling queue.
    # Backups are kept in a reserve dictionary for quick lookup.
    
    primary_queue = [a for a in activities if a.id.endswith('_p')]
    
    # Create lookup map: {'act_001_b': ActivityObject, ...}
    backup_reserve = {a.id: a for a in activities if a.id.endswith('_b')}

    logger.info(f"📋 Scheduling {len(primary_queue)} Primaries (Held {len(backup_reserve)} Backups in reserve)")
    
    scheduler = AdaptiveScheduler(
        activities=primary_queue,  # <--- ONLY PRIMARIES PASSED HERE
        specialists=resources['specialists'],
        equipment=resources['equipment'],
        travel_periods=resources['travel'],
        start_date=start_date,
        duration_days=90,
        backup_lookup=backup_reserve # <--- NEW ARGUMENT (Ensure Engine accepts this!)
    )

    # Run the Solver
    final_state = scheduler.run()

    # --- PHASE 3: REPORTING ---
    stats = final_state.get_statistics()
    
    print("\n" + "="*50)
    print("📊 FINAL EXECUTION REPORT")
    print("="*50)
    print(stats)
    
    # Optional: Detailed Breakdown
    # print(f"Total Slots Booked:    {stats['total_slots']}")
    # print(f"  - Primary Goals:     {stats['primary_slots']}")
    # print(f"  - Backup (Fallback): {stats['backup_slots']}")
    # print(f"Resilience Rate:       {stats['resilience_rate']}% (Adaptive substitutions)")
    
    if stats.get('failed_activities_count', 0) > 0:
        print("\n🔍 FAILURE ANALYSIS (Top 20)")
        report = final_state.get_failure_report()
        for fail in report: 
            print(f"❌ [P{fail['priority']}] {fail['activity_name']}")
            print(f"   Reason: {fail['latest_reason']}")

    # --- PHASE 4: EXPORT FOR FRONTEND ---
    # Combine all activities for lookup
    all_activities = {a.id: a for a in primary_queue}
    all_activities.update(backup_reserve)
    
    # Export
    export_dashboard_data(final_state, all_activities, resources['travel'], "health-dashboard-ui/public/dashboard_data.json")

    print("\n✅ Integration Test Complete.")

if __name__ == "__main__":
    main()