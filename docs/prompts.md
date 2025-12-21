# 🤖 Generative AI Prompts

The Data Factory uses **Google Gemini 1.5 Flash** to generate synthetic data. To ensure the output matches our strict Pydantic schemas, we use "Strong Prompts" that explicitly define JSON structures, allowed Enums, and logical constraints.

Below are the raw prompts used for each data category.

---

## 1. Activity Generation Prompt

**Purpose:** Generates linked pairs of Primary and Backup activities.
**Strategy:** "Big Bang" Batching (50+ pairs in one call).

```text
Generate {count} pairs of health activities (Primary + Backup) for a wellness plan starting {start_date}.

OUTPUT FORMAT: 
A single valid JSON Array containing {count} objects.

STRICT SCHEMA RULES (Follow exactly to avoid validation errors):

1. OBJECT STRUCTURE:
    {
      "primary": { ...Activity Details... },
      "backup": { ...Activity Details... }
    }

2. VALID "type" VALUES (Do NOT use 'Cardio' or 'Nutrition'):
    ["Fitness", "Food", "Medication", "Therapy", "Consultation", "Other"]

3. VALID "frequency" PATTERNS (Do NOT use 'W', 'Bi-Weekly' or 'CUSTOM'):
    ["Daily", "Weekly", "Monthly"]
    
4. DURATION RULES:
    - "duration_minutes": Must be an INTEGER between 15 and 60. (Only 10% can be up to 90).
    - "preparation_duration_minutes": Integer between 0 and 15.
    - KEEP IT SHORT: We are scheduling a busy human, not a robot. Prefer 30-45 min sessions.

5. REQUIRED FIELDS:
    - "id" (string)
    - "name" (string)
    - "type" (Enum above)
    - "priority" (int 1-5)
    - "duration_minutes" (int)
    - "preparation_duration_minutes" (int)
    - "frequency": { "pattern": "Weekly", "count": 3 }
    - "specialist_id" (string or null)
    - "equipment_ids" (list of strings)
    - "backup_activity_ids" (list of strings)

6. LOGIC:
    - "primary": High commitment (Gym, Specialist).
    - "backup": Low friction (Home, No Equipment). MUST be 100% Equipment-Free or use only "Portable" items (e.g. Bands, Mat).
    - PRIORITY DISTRIBUTION: You MUST generate a mix of Priorities 1, 2, 3, 4, and 5. Do not default everyone to 3 or 4.
    - FREQUENCY BALANCE: Avoid overloading the schedule. 
      - Prefer "Weekly" (1-3 times) over "Daily".
      - If "Daily", duration MUST be under 20 minutes.

```

---

## 2. Resource Generation Prompts

### A. Specialists

**Purpose:** Creates human resources with shift availability.

```text
Generate {specialist_count} healthcare specialists.
OUTPUT: JSON Array.
VALID TYPES: ["Trainer", "Dietitian", "Therapist", "Physician", "Allied_Health"]

CRITICAL RULES:
- "id": Must be a STRING (e.g., "S001").
- "days_off": Must be a list of DATE STRINGS "YYYY-MM-DD" (e.g. ["2025-12-25"]). 
  (Do NOT use integers like 0 or 6. If no specific holidays, use empty list).

FIELDS: id, name, type, availability (list of objects: { "day_of_week": 0-6, "start_time": "HH:MM:SS", "end_time": "HH:MM:SS" }), days_off, max_concurrent_clients.

```

### B. Equipment

**Purpose:** Creates physical assets with portability flags.

```text
Generate {equipment_count} equipment items.
OUTPUT: JSON Array.

RULES:
- "id": Must be a STRING (e.g., "E001").

FIELDS: id, name, location, is_portable (bool), maintenance_windows (list of objects with start_date/end_date YYYY-MM-DD), max_concurrent_users.

```

### C. Travel Periods

**Purpose:** Creates simulation constraints (User location context).
**Context Injection:** We inject valid equipment IDs (`{ids_str}`) into the prompt to ensure the "Hotel Gym" has valid gear.

```text
Generate {travel_count} travel periods starting {start_date}.
OUTPUT: JSON Array.

RULES:
- "id": Must be a STRING (e.g., "E001").

FIELDS: id, location, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), remote_activities_only (bool).

CONSTRAINT: If location is 'Hotel/Resort', populate 'available_equipment_ids' from this list: {ids_str}.

```