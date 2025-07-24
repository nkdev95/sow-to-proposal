# --- agents/data_extraction_agent.py ---
# Agent responsible for extracting structured information from raw SOW text.

import json
from agents.llm_connector import _call_llm # Import the shared LLM caller

def data_extraction_agent_run(sow_text: str, llm_choice: str = "openai") -> dict:
    """
    Agent responsible for extracting structured information from raw SOW text.
    """
    if not sow_text:
        return {"error": "No SOW text provided for extraction."}

    sow_text_limited = sow_text[:15000] # Limit input to manage token costs

    system_instruction = "You are an expert AI assistant specialized in analyzing Scope of Work (SOW) documents. Your goal is to extract precise and comprehensive information into a structured JSON object. Adhere strictly to the requested schema and data types."
    user_prompt = f"""
    Read the following Scope of Work (SOW) text carefully and extract ALL the key information into a structured JSON object.
    Be precise, comprehensive, and accurate.

    **Strict JSON Schema Adherence:**
    - If a field is not explicitly mentioned or clearly derivable, return an empty array `[]` for list fields, and "N/A" for single string fields.
    - Do NOT return "N/A" inside a list. If a list has no content, return `[]`.
    - For "deliverables", each item in the list MUST be an object with "name" (string) and "description" (string) keys.

    **Key Field Extraction Guidelines:**
    - **"project_name"**: Identify the official or implied name of the project. Look for titles, headings, or the main subject discussed. If ambiguous, use the most prominent phrase.
    - **"client_name"**: Identify the full name of the client or organization issuing the SOW. Look for "Client:", "Customer:", "Issued By:", "For:", "Organization Name:", or the primary entity requesting the work.
    - **"timeline_overview"**: Extract descriptions of project duration, phases, key milestones, or important dates. This should be a list of strings.

    SOW Text:
    ---
    {sow_text_limited}
    ---

    Extract the following fields into a JSON object:
    - "project_name": (string)
    - "client_name": (string)
    - "objectives": (list of strings) Concise main goals or aims of the project.
    - "scope_of_work": (list of strings) Detailed summary of activities, tasks, and responsibilities explicitly INCLUDED.
    - "out_of_scope": (list of strings) Detailed summary of activities, tasks, or responsibilities explicitly EXCLUDED.
    - "deliverables": (list of objects) Tangible outputs/results. Each object: {{"name": "string", "description": "string"}}.
      Example: {{"name": "Phase 1 Report", "description": "Detailed analysis and recommendations"}}
    - "technical_requirements": (list of strings) Specific technologies, platforms, tools, standards, or methodologies.
    - "key_constraints": (list of strings) Significant limitations, assumptions, risks, or conditions.
    - "stakeholders": (list of strings) Key roles, teams, or departments involved (client and vendor side).
    - "timeline_overview": (list of strings) Project duration, phases, or key milestones.

    Return only the JSON object.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    response_content = _call_llm(messages, response_format="json_object", llm_choice=llm_choice)
    try:
        parsed_data = json.loads(response_content)

        # --- Post-deserialization cleanup for list fields and string fields ---
        # Helper to ensure a field is a list of strings, converting if necessary and cleaning "N/A"
        def ensure_list_of_strings(field_value):
            if isinstance(field_value, list):
                cleaned_list = [item for item in field_value if isinstance(item, str) and item.lower() != "n/a"]
                return cleaned_list
            elif isinstance(field_value, str) and field_value.lower() == "n/a":
                return []
            return []

        # Apply cleanup to all list fields
        for key in ["objectives", "scope_of_work", "out_of_scope", "technical_requirements",
                     "key_constraints", "stakeholders", "timeline_overview"]:
            parsed_data[key] = ensure_list_of_strings(parsed_data.get(key))

        # Special handling for Deliverables (List of Maps)
        cleaned_deliverables = []
        raw_deliverables = parsed_data.get("deliverables")
        if isinstance(raw_deliverables, list):
            for item in raw_deliverables:
                if isinstance(item, dict) and "name" in item and "description" in item:
                    cleaned_deliverables.append(item)
                elif isinstance(item, str) and item.lower() != "n/a":
                    # If LLM returns a list of strings for deliverables, convert to expected format
                    cleaned_deliverables.append({"name": item, "description": "Not detailed by AI"})
        parsed_data["deliverables"] = cleaned_deliverables

        # Basic validation for single string fields to ensure they are not null or empty
        for key in ["project_name", "client_name"]:
            if not parsed_data.get(key) or (isinstance(parsed_data.get(key), str) and parsed_data.get(key).lower() == "n/a"):
                parsed_data[key] = "N/A"

        return parsed_data
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from LLM: {response_content}")
        return {"error": "Failed to parse LLM response as JSON. Raw LLM output: " + response_content[:500]}
    except Exception as e:
        print(f"An unexpected error occurred during SOW analysis: {e}")
        return {"error": f"An unexpected error occurred: {e}"}