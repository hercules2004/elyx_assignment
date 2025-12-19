"""
LLM-powered data generator for the Adaptive Health Allocator.
STRATEGY: 'Big Bang' Batching (1 Request per Category) to bypass RPM limits.
UPDATED: Strong Prompts + Robust Parsing = Zero Validation Errors.
"""

import os
import json
import logging
import re
import google.generativeai as genai
from typing import List, Tuple, Dict, Any, Type
from datetime import date
from pydantic import ValidationError, BaseModel

# Import your models
from models import Activity, Specialist, Equipment, TravelPeriod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataGenerator:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found. Please set it in environment.")

        genai.configure(api_key=self.api_key)
        
        # [MAGIC SAUCE] Use the high-throughput Flash 1.5 model
        self.model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025") 
        self.total_cost = 0.0

    def _estimate_cost(self, prompt_tokens: int, response_tokens: int) -> float:
        return (prompt_tokens * 0.075 + response_tokens * 0.30) / 1_000_000

    def _robust_parse_json(self, raw_text: str) -> List[Any]:
        """
        🛡️ ROBUST PARSER: Handles Markdown stripping and shape normalization.
        """
        if not raw_text: return []

        # 1. Clean Markdown Code Blocks
        clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()
        
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback: Try to regex extract the main list
            match = re.search(r'(\[.*\])', clean_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except: return []
            else:
                return []

        # 2. Normalize Data Shape
        if isinstance(data, list): return data
        if isinstance(data, dict):
            for key in ['activities', 'specialists', 'equipment', 'travel', 'result']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return []

    def _fetch_big_batch(self, prompt: str, model_class: Type[BaseModel]) -> Tuple[List[Any], float]:
        """
        Executes a generation request with robust parsing.
        """
        try:
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=16000, 
                temperature=0.7
            )

            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            cost = 0.0
            if hasattr(response, 'usage_metadata'):
                p_tok = response.usage_metadata.prompt_token_count
                r_tok = response.usage_metadata.candidates_token_count
                cost = self._estimate_cost(p_tok, r_tok)
            self.total_cost += cost

            data_list = self._robust_parse_json(response.text)
            
            valid_items = []
            for i, item in enumerate(data_list):
                try:
                    valid_items.append(model_class(**item))
                except ValidationError as e:
                    logger.warning(f"Skipping invalid item {i} in batch: {e.json()}")
                    continue
            
            return valid_items, cost

        except Exception as e:
            logger.error(f"Batch Generation Failed: {e}")
            return [], 0.0

    def generate_resilient_activities(self, count: int = 50, start_date: date = None) -> Tuple[List[Activity], float]:
        """
        Generates Activities using a STRONG SCHEMA PROMPT.
        """
        if start_date is None: start_date = date.today()

        # 🔥 STRONG PROMPT: Explicitly lists valid Enums and Schema Rules
        prompt = f"""
        Generate {count} pairs of health activities (Primary + Backup) for a wellness plan starting {start_date}.
        
        OUTPUT FORMAT: 
        A single valid JSON Array containing {count} objects.
        
        STRICT SCHEMA RULES (Follow exactly to avoid validation errors):
        
        1. OBJECT STRUCTURE:
           {{
             "primary": {{ ...Activity Details... }},
             "backup": {{ ...Activity Details... }}
           }}
        
        2. VALID "type" VALUES (Do NOT use 'Cardio' or 'Nutrition'):
           ["Fitness", "Food", "Medication", "Therapy", "Consultation", "Other"]
        
        3. VALID "frequency" PATTERNS (Do NOT use 'W', 'Bi-Weekly' or 'CUSTOM'):
           ["Daily", "Weekly", "Monthly"]
           
        4. DURATION RULES:
           - "duration_minutes": Must be an INTEGER between 10 and 120.
           - NEVER use 0, 1, 2, or 5 minutes. Minimum is 10.
           - "preparation_duration_minutes": Integer between 0 and 30.

        5. REQUIRED FIELDS:
           - "id" (string)
           - "name" (string)
           - "type" (Enum above)
           - "priority" (int 1-5)
           - "duration_minutes" (int)
           - "preparation_duration_minutes" (int)
           - "frequency": {{ "pattern": "Weekly", "count": 3 }}
           - "specialist_id" (string or null)
           - "equipment_ids" (list of strings)
           - "backup_activity_ids" (list of strings)

        6. LOGIC:
           - "primary": High commitment (Gym, Specialist).
           - "backup": Low friction (Home, No Equipment). MUST be 100% Equipment-Free or use only "Portable" items (e.g. Bands, Mat).
           - PRIORITY DISTRIBUTION: You MUST generate a mix of Priorities 1, 2, 3, 4, and 5. Do not default everyone to 3 or 4.
        """
        
        logger.info(f"🚀 Launching 'Big Bang' request for {count} activity pairs...")
        
        try:
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                max_output_tokens=16000
            )
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            # Cost tracking
            p_tok = self.model.count_tokens(prompt).total_tokens
            r_tok = self.model.count_tokens(response.text).total_tokens
            cost = self._estimate_cost(p_tok, r_tok)
            self.total_cost += cost

            # Parse
            raw_data = self._robust_parse_json(response.text)
            print(raw_data)
            final_activities = []
            
            for i, pair in enumerate(raw_data):
                prim = pair.get('primary')
                back = pair.get('backup')
                if not prim or not back: continue

                # Hard-code IDs for linking
                prim['id'] = f"act_{i:03d}_p"
                back['id'] = f"act_{i:03d}_b"
                prim['backup_activity_ids'] = [back['id']]
                
                # --- SAFETY NET: Light Normalization ---
                # Even with strong prompts, it's safe to Title Case these fields
                for act in [prim, back]:
                    if 'type' in act: 
                        act['type'] = str(act['type']).title()
                    if 'frequency' in act and 'pattern' in act['frequency']:
                        act['frequency']['pattern'] = str(act['frequency']['pattern']).title()

                try:
                    final_activities.append(Activity(**prim))
                    final_activities.append(Activity(**back))
                except ValidationError as e:
                    logger.error(f"❌ Validation Failed for Pair {i}: {e.json()}")
                    continue
            
            logger.info(f"✅ Generated {len(final_activities)} activities in one shot.")
            return final_activities, cost

        except Exception as e:
            logger.error(f"Activity Batch Failed: {e}")
            return [], 0.0

    def generate_resources(self, specialist_count: int = 15, equipment_count: int = 15, travel_count: int = 5, start_date: date = None) -> Tuple[Dict[str, List], float]:
        if start_date is None: start_date = date.today()
        step_cost = 0.0
        
        logger.info("Generating Resources (3 API Calls)...")

        # 1. Specialists - Strong Prompt
        prompt_spec = f"""
        Generate {specialist_count} healthcare specialists.
        OUTPUT: JSON Array.
        VALID TYPES: ["Trainer", "Dietitian", "Therapist", "Physician", "Allied_Health"]
        CRITICAL RULES:
        - "id": Must be a STRING (e.g., "S001").
        - "days_off": Must be a list of DATE STRINGS "YYYY-MM-DD" (e.g. ["2025-12-25"]). 
          (Do NOT use integers like 0 or 6. If no specific holidays, use empty
        FIELDS: id, name, type, availability (list of objects: {{ "day_of_week": 0-6, "start_time": "HH:MM:SS", "end_time": "HH:MM:SS" }}), days_off, max_concurrent_clients.
        """
        specs, c1 = self._fetch_big_batch(prompt_spec, Specialist)
        step_cost += c1
        
        # 2. Equipment - Strong Prompt
        prompt_eq = f"""
        Generate {equipment_count} equipment items.
        OUTPUT: JSON Array.
        RULES:
        - "id": Must be a STRING (e.g., "E001").
        FIELDS: id, name, location, is_portable (bool), maintenance_windows (list of objects with start_date/end_date YYYY-MM-DD), max_concurrent_users.
        """
        equips, c2 = self._fetch_big_batch(prompt_eq, Equipment)
        step_cost += c2
        
        # 3. Travel - Strong Prompt
        # Extract ID subset for context
        valid_ids = [e.id for e in equips[:5]] 
        ids_str = json.dumps(valid_ids)
        
        prompt_tr = f"""
        Generate {travel_count} travel periods starting {start_date}.
        OUTPUT: JSON Array.
        RULES:
        - "id": Must be a STRING (e.g., "E001").
        FIELDS: id, location, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), remote_activities_only (bool).
        CONSTRAINT: If location is 'Hotel/Resort', populate 'available_equipment_ids' from this list: {ids_str}.
        """
        travels, c3 = self._fetch_big_batch(prompt_tr, TravelPeriod)
        step_cost += c3

        return {
            "specialists": specs,
            "equipment": equips,
            "travel": travels
        }, step_cost