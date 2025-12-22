# 🏛️ System Architecture

The **Adaptive Health Allocator** is built on a modular **3-Stage Pipeline**: Generation, Scheduling, and Presentation. This architecture decouples the "World Creation" (GenAI) from the "World Solving" (Algorithms), ensuring that the scheduler is deterministic and testable even though the input data is dynamic.

---

## 🏗️ High-Level Diagram

```mermaid
graph TD
    A[User / Config] -->|API Key + Constraints| B(Data Factory Layer)
    B -->|Big Bang Prompt| C{Gemini 1.5 Flash}
    C -->|Raw JSON| D[Sanitization & Parsing]
    D -->|Pydantic Models| E[Clean Data Objects]
    
    E --> F(Adaptive Engine Layer)
    F -->|Liquid Scheduling| G{Constraint Checker}
    G -->|Valid Slot?| H[Schedule State]
    G -->|Conflict?| I[Fallback / Resilience Logic]
    I -->|Swap to Backup| H
    
    H -->|Final State| J(Presentation Layer)
    J -->|JSON Export| K[React Dashboard]

```


## 1. Data Models (Schema & Enums)

The system relies on strict typing via **Pydantic Models** (`models.py`) to ensure data integrity across the pipeline.

### Core Entities

| Model | Purpose | Key Fields | Allowed Values (Enums) |
| --- | --- | --- | --- |
| **Activity** | Represents a single task | `id`, `type`, `priority`, `frequency` | **Types:** Fitness, Food, Medication, Therapy, Consultation.<br><br>**Frequency:** Daily, Weekly, Monthly. |
| **Specialist** | A human resource | `id`, `type`, `availability` | **Types:** Trainer, Therapist, Doctor, Nutritionist. |
| **TravelPeriod** | A context modifier | `location_type`, `remote_only` | **Locations:** Home, Hotel, Remote (Cabin/Camping). |
| **Equipment** | A physical resource | `id`, `is_portable` | **Portable:** True (Mat, Bands) or False (Treadmill). |

### Validation Rules

* **Priority:** Integer `1` (Critical) to `5` (Optional).
* **Duration:** Minimum `10` minutes.
* **Backup Link:** `backup_activity_ids` must reference a valid Activity ID in the same generation batch.

---

## 2. State Management (The "Memory")

**Role:** The "Ledger" that tracks truth.

The **`ScheduleState`** class is the single source of truth during the scheduling run. It is mutable and evolves as the engine iterates through days. It captures not just *what happened*, but *why* things failed.

### State Components Table

| Component | Type | Description | Why it matters |
| --- | --- | --- | --- |
| **`schedule`** | `Dict[Date, List[Slot]]` | The master timeline. Maps every date to a list of booked slots. | This is the final output that the UI renders. |
| **`daily_load`** | `Dict[Date, LoadMap]` | A heatmap tracking how many tasks of each priority are booked per day. | Used by the **Liquid Logic** to prevent burnout (e.g., "Max 2 High-Intensity tasks/day"). |
| **`weekly_counter`** | `Dict[ActivityID, Int]` | Tracks progress toward weekly quotas (e.g., "2/3 Gym Sessions"). | Allows tasks to "flow" to other days. If the counter isn't full, the task remains pending. |
| **`failed_activities`** | `List[FailureLog]` | A forensic log of every rejected task. | **Critical for Trust.** Stores the exact reason (e.g., "Blocked by Travel") so the UI can explain it to the user. |
| **`booked_slots`** | `List[TimeSlot]` | A flat list of all confirmed bookings. | Used for O(1) collision detection (Overlap checks). |

---

## 3. The Adaptive Engine Layer (Scheduler)

**Role:** The "Brain" that solves the time-allocation problem.

### Core Logic: Liquid Scheduling

Traditional schedulers are rigid ("Gym is on Monday"). Our engine uses **Liquid Weekly Quotas**:

1. **The Bucket:** Each activity has a quota (e.g., "3 times/week").
2. **The Flow:** The scheduler iterates through days. If Monday is full (or blocked by travel), the task "flows" naturally to Tuesday.
3. **Completion:** The engine is satisfied as soon as the *Quota* is met, regardless of the specific day.

### The Fallback Chain (Resilience Module)

When a high-priority task is blocked, the engine triggers a **Resilience Loop**:

1. **Primary Attempt:** Try to schedule "Heavy Lifting (Gym)".
2. **Failure Detection:** Blocked by "Travel (Remote Cabin)".
3. **Immediate Swap:** The engine retrieves the linked **Backup Activity** ("Bodyweight Flow").
4. **Diplomatic Immunity:** The backup is scheduled *immediately* on the same day, counting towards the Primary's weekly quota.

---

Here is a comprehensive breakdown of the Constraint Validation logic, including flowcharts to visualize the decision-making process.

---

## 4. Constraint Validation (Guardrails)

**Role:** The "Gatekeeper" that enforces physical reality.

Located in `scheduler/constraints.py`, this module does not care about user preferences. It answers a binary question: *"Is it physically possible for Activity X to happen at Time Y?"*

It uses a **"Fail Fast" Hierarchy**. It runs the cheapest and most restrictive checks first (like "Are you in another country?") before running expensive or granular checks (like "Do you have a 15-minute gap?").

### 1. The Master Validation Pipeline (`check_time_slot`)

This is the main entry point. Every single potential slot must survive this gauntlet to be considered valid.

```mermaid
flowchart TD
    Start([Start Check]) --> Travel{1. Travel Context}
    
    Travel -- Violation --> Fail([Return Violation])
    Travel -- Pass --> Specialist{2. Specialist Available?}
    
    Specialist -- Not Working --> Fail
    Specialist -- Pass --> Equipment{3. Equipment Check}
    
    Equipment -- Missing/Broken --> Fail
    Equipment -- Pass --> Overlap{4. Time Overlap}
    
    Overlap -- Collision --> Fail
    Overlap -- Pass --> Window{5. Time Window}
    
    Window -- Too Early/Late --> Fail
    Window -- Pass --> Success([✅ VALID SLOT])
    
    style Fail fill:#ffcccc,stroke:#333,stroke-width:2px
    style Success fill:#9f9,stroke:#333,stroke-width:2px

```

---

### 2. Deep Dive: Travel & Location Logic (`_check_travel_context`)

This is the most complex logic block. It determines if a task can be performed given the user's current geographic location. This is where the **"Diplomatic Immunity"** pattern and **"Smart Portability"** inference happen.

#### The Logic Flow

1. **Am I traveling?** If no, skip everything.
2. **Diplomatic Immunity:** If this is a `Backup` activity (e.g., "Hotel Room Workout"), we **assume** it is portable and bypass location checks.
3. **Portability Inference:** If the activity isn't explicitly marked "Remote," the system checks the equipment. If you only need a *Yoga Mat* (Portable: Yes), the system infers the activity is effectively remote.
4. **Location Enforcement:** If the trip is "Remote Cabin" (Nature only), it bans tech-heavy tasks. If the trip is "Hotel," it bans "Home-only" tasks.

```mermaid
flowchart TD
    Start([Check Travel]) --> IsTraveling{Is User Traveling?}
    
    IsTraveling -- No --> Pass([✅ Pass])
    IsTraveling -- Yes --> IsBackup{Is Backup Activity?}
    
    IsBackup -- Yes (Immunity) --> Pass
    IsBackup -- No --> CheckRemote{Is Remote Capable?}
    
    CheckRemote -- Yes --> RemoteType{Trip Type}
    CheckRemote -- No --> CheckEquip{All Equipment Portable?}
    
    CheckEquip -- Yes (Inferred Remote) --> RemoteType
    CheckEquip -- No --> Fail([❌ Fail: Not Portable])
    
    RemoteType -- Remote Trip (Nature) --> CheckNature{Is Remote Only?}
    RemoteType -- City Trip --> CheckHome{Location == Home?}
    
    CheckNature -- Activity is Digital --> Fail([❌ Fail: Trip is Detox])
    CheckNature -- Activity is Remote --> Pass
    
    CheckHome -- Yes --> Fail([❌ Fail: Activity stuck at Home])
    CheckHome -- No --> Pass

```

---

### 3. Deep Dive: Equipment & Hotel Gyms (`_check_equipment`)

This logic solves the "Hotel Gym" problem. Just because you are traveling doesn't mean you can't use a treadmill—you just need to use the *Hotel's* treadmill.

#### The Logic Flow

1. **Iterate Equipment:** Check every item needed (e.g., Treadmill, Weights).
2. **Context Check:** Are we at Home or Traveling?
* **If Home:** Is the machine broken (Maintenance)? Is it full (Concurrency)?
* **If Traveling:** Is the item portable? OR Does the Hotel provide it?



```mermaid
flowchart TD
    Start([Check Equipment]) --> Loop{For Each Item}
    
    Loop -- Done --> Pass([✅ Pass])
    Loop -- Next Item --> Context{Traveling?}
    
    Context -- No (Home) --> Maint{Under Maintenance?}
    Maint -- Yes --> Fail([❌ Fail: Broken])
    Maint -- No --> Usage{Too Many Users?}
    Usage -- Yes --> Fail([❌ Fail: Full])
    Usage -- No --> Loop
    
    Context -- Yes (Travel) --> Portable{Is Portable?}
    Portable -- Yes --> Loop
    Portable -- No --> Hotel{Available at Destination?}
    
    Hotel -- Yes (Hotel Gym) --> Loop
    Hotel -- No --> Fail([❌ Fail: Missing Resource])

```

---

### 4. Deep Dive: Time Overlap with Prep Time (`_check_overlap`)

The standard scheduler mistake is checking `Start` vs `End`. This system implements **"Effective Time"** blocking.

If a task starts at **10:00 AM** but requires **15 mins prep/travel**, the system views the "Effective Start" as **9:45 AM**.

**The Logic:**
The system calculates a collision if:

$$
(\text{New.Start} - \text{New.Prep}) < (\text{Old.End}) \quad \text{AND} \quad (\text{Old.Start} - \text{Old.Prep}) < (\text{New.End})
$$

**Visual Representation:**

* **Scenario:** You try to book a "Zoom Call" at 9:45 AM.
* **Conflict:** Even though the Gym starts at 10:00 AM, the time 9:45 AM is blocked by "Driving to Gym."
* **Result:** `ConstraintViolation: Overlap`.
---

## 5. The Data Factory Layer (Generators)

**Role:** The "Creator" that builds the simulation world.

### Key Components

* **`generators/data_factory.py`**: The main entry point.
* **"Big Bang" Strategy:** Instead of making 50 small API calls (which hits rate limits), we issue **one massive prompt** requesting all 50 activity pairs at once. This reduces latency by ~80%.
* **Sanitization Loop:** A custom logic layer that sits *between* the LLM response and Pydantic validation. It auto-corrects common errors:
* *Frequency Fix:* Converts hallucinated "Custom" patterns to "Weekly".
* *Duration Fix:* Bumps impossible "2-minute" workouts to a minimum of 10 minutes.
