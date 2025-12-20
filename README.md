# Adaptive Health Allocator 🏥

**An AI-powered scheduling engine that adapts to real life.**

> *Most scheduling apps break when you miss a task. This one adapts.*

The **Adaptive Health Allocator** is a resilient scheduling system designed to manage complex health routines under real-world constraints like travel, limited capacity, and resource shortages. Unlike rigid calendars that treat a missed gym session as a failure, this system uses **Liquid Scheduling** and **Fallback Chains** to negotiate with your reality. It doesn't just tell you *what* to do; it figures out *how* you can still achieve your goals when life gets in the way.

---

## 🌟 Key Highlights

* **🛡️ 15.2% Resilience Rate:** The system automatically recovers from failure by swapping blocked activities with viable backups (e.g., Gym  Home Workout) without user intervention.
* **📈 100% Critical Success:** Achieved perfect adherence for Priority 1 (Critical) and Priority 2 (High) tasks, ensuring the most important health goals are never missed.
* **💧 Liquid Scheduling:** Tasks are not locked to specific days. If Monday is full, the engine automatically flows tasks to Tuesday or Wednesday to meet weekly quotas.
* **🌍 Travel-Proof:** Smart constraints understand context. The system automatically blocks gym tasks when you are in a "Remote Cabin" but allows portable activities to proceed.

---

## 🚀 Quick Start

### 1. Prerequisites

* Python 3.10+
* Node.js 18+ (for UI)
* Google Gemini API Key

### 2. Setup Backend (The Engine)

```bash
# Clone the repository
git clone https://github.com/your-username/adaptive-health-allocator.git
cd adaptive-health-allocator

# Install Python dependencies
pip install -r requirements.txt

# Set your API Key
export GOOGLE_API_KEY="your_gemini_key_here"

```

### 3. Run the Pipeline

The system operates in two phases: **Generation** (creating the world) and **Scheduling** (solving the time).

```bash
# 1. Generate Data & Run the Scheduler
# This script fetches data from Gemini, runs the engine, and exports JSON for the UI.
python run_scheduler.py

```

* *Note: First run will take ~30s to generate data. Subsequent runs use cached `debug_data.json`.*

### 4. Launch the Dashboard (The UI)

```bash
cd frontend
npm install
npm run dev

```

Open `http://localhost:3000` to see your adaptive schedule.

---

## 📊 Performance Results

We benchmarked the system over a 90-day simulation with heavy travel constraints and resource scarcity. The new "Balanced Load" strategy significantly improved overall throughput.

### Overall Metrics

| Metric | Rigid Scheduler | **Adaptive Allocator** | Impact |
| --- | --- | --- | --- |
| **Overall Success Rate** | ~40% | **91.2%** | **Highly Optimized Flow** |
| **Resilience Rate** | 0.0% | **15.2%** | **Auto-recovered failures** |
| **Backup Usage** | 0 | **44+** | Diplomatic Immunity active |

### Priority Breakdown (Success Rate)

The system prioritizes "Big Rocks" (P1/P2) first, ensuring critical health tasks survive. With improved load balancing, even lower-priority tasks now have high completion rates.

| Priority Level | Success Rate | Status |
| --- | --- | --- |
| **P1 (Critical)** | **100.0%** (120/120) | ✅ Perfect Adherence |
| **P2 (High)** | **100.0%** (54/54) | ✅ Perfect Adherence |
| **P3 (Medium)** | **88.6%** (226/255) | ✅ Strong Performance |
| **P4 (Low)** | **100.0%** (21/21) | ✅ Excellent |
| **P5 (Optional)** | **64.1%** (25/39) | ⚠️ Acceptable Drop-off |

> *Note: P5 (Optional) tasks are the first to be sacrificed when the day is full, which mimics realistic human prioritization.*

---

## 🧠 Architecture & Algorithms

The system uses a **3-Stage Pipeline** to transform vague goals into specific time slots.

### 1. The Generative Layer (`generators/`)

* **Strategy:** "Big Bang" Batching using Gemini 1.5 Flash.
* **Sanitization:** A robust parsing layer that auto-corrects LLM errors (e.g., fixing "Custom" frequencies or invalid JSON schemas) before they reach the engine.

### 2. The Constraint Engine (`scheduler/constraints.py`)

* **Hard Constraints:** Enforces physical reality.
* **Resource Check:** Is the Specialist available? Is the Equipment broken?
* **Travel Context:** "User is in a Remote Cabin"  Blocks Gym, allows Portable gear.
* **Time Windows:** Respects strict medication windows (e.g., "8:00 AM - 10:00 AM").



### 3. The Liquid Scheduler (`scheduler/engine.py`)

* **Algorithm:** Heuristic Scoring + Weekly Quotas.
* **Liquid Logic:** Instead of rigid "Mon/Wed/Fri" slots, the engine uses **Weekly Quotas**. blocked tasks automatically "flow" to the next available day.
* **Fallback Chains:** If a Primary Activity (P1) fails today, the engine immediately attempts to schedule its linked **Backup Activity** (P2) *before* giving up on the day.

---

## 📚 Documentation Deep Dives

For detailed engineering breakdowns, see the `docs/` folder:

* **[🏛️ System Architecture](https://www.google.com/search?q=./docs/architecture.md)** - Diagram of the Data Factory, Engine, and State Manager.
* **[📐 Low-Level Design](https://www.google.com/search?q=./docs/system_design.md)** - Class diagrams, Pydantic models, and method signatures.
* **[🧪 Evaluation & Testing](https://www.google.com/search?q=./docs/evaluation.md)** - Failure analysis logs and resilience metrics breakdown.

---

## 🎨 UI Features

The frontend is designed to be forgiving and transparent, removing the guilt associated with missed tasks.

* **"Why is this here?":** A simple header that instantly tells you if you are in **Travel Mode** or **Home Mode**, so you know why your schedule changed.
* **The "Panic Button":** Every activity has a **Swap 🔄** icon. One click reveals the pre-calculated Backup option (e.g., "Switch Gym to Home Workout?").
* **Smart Calendar:** A monthly view that uses color coding to show travel days and high-intensity weeks at a glance.
* **The "Skipped" List:** Transparently lists what was skipped today and the exact reason (e.g., "Blocked by Travel"), building trust in the AI.

---

## 💡 Key Design Decisions

1. **Diplomatic Immunity for Backups:**
* *Problem:* Strict location rules blocked "Home Workouts" when the user was at a "Hotel."
* *Solution:* Backup activities are granted immunity from location checks, assuming they are low-friction/portable.


2. **Liquid Weekly Quotas:**
* *Problem:* Rigid "Daily" schedules caused gridlock when one day was busy.
* *Solution:* We track `weekly_counter`. As long as the task happens  times/week, the specific day doesn't matter.


3. **The "Pyramid" Distribution:**
* *Problem:* High-priority tasks monopolized the calendar, leaving 0% room for hobbies (P5).
* *Solution:* Adjusted Data Generation to enforce a 10/20/40/30 split across priority tiers to ensure realistic load balancing.



---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **AI Model:** Google Gemini 1.5 Flash (via `google-generativeai`)
* **Validation:** Pydantic (Strict Schema Enforcement)
* **Frontend:** React (Vite), Tailwind CSS, Lucide Icons
* **Logging:** Python `logging` module with forensic failure analysis.

---

## 🤝 Acknowledgments

* **Google Gemini Team:** For the Flash 1.5 model that made data generation affordable.
* **Vercel v0:** For accelerating the UI prototyping process.
* **Elyx-assignment:** Design inspired by the Elyx Assignment.docx requirements
