# --- llm_agents.py ---
# This file contains the core AI agent logic, now explicitly structured for multi-agent roles.

import os
import json
from openai import OpenAI
import google.generativeai as genai

# --- LLM Clients Initialization (Placeholders) ---
# These clients will be initialized by app.py based on user's LLM_CHOICE and API key availability.
# They are global variables that app.py will set.
openai_client = None
gemini_model = None

def _call_llm(messages: list, response_format: str = "text", llm_choice: str = "openai") -> str:
    """
    Internal helper to call the chosen LLM (OpenAI or Gemini).
    Args:
        messages (list): A list of message dictionaries for the chat completion.
                         Expected format: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
                         or [{"role": "user", "content": "..."}]
        response_format (str): "text" for plain text, "json_object" for JSON output.
        llm_choice (str): "openai" or "gemini".
    Returns:
        str: The content from the LLM response.
    Raises:
        ValueError: If the LLM choice is not supported or client is not initialized.
    """
    try:
        if llm_choice == "openai":
            if not openai_client:
                raise ValueError("OpenAI client not initialized. Check API key.")
            response = openai_client.chat.completions.create(
                model="gpt-4o", # Using gpt-4o for better quality. Can use "gpt-3.5-turbo" for faster, cheaper, but less capable results
                messages=messages,
                response_format={"type": "json_object"} if response_format == "json_object" else None,
                temperature=0.4 # Lower temperature for more factual/less creative output
            )
            return response.choices[0].message.content
        elif llm_choice == "gemini":
            if not gemini_model:
                raise ValueError("Gemini model not initialized. Check API key.")

            # --- Gemini specific message formatting ---
            # Gemini expects messages in the format: [{"role": "user", "parts": [{"text": "..."}]}]
            # System instructions are often incorporated into the user prompt for Gemini.
            gemini_messages = []
            user_content = ""
            for msg in messages:
                if msg["role"] == "system":
                    user_content += msg["content"] + "\n\n" # Prepend system content to user prompt
                elif msg["role"] == "user":
                    user_content += msg["content"]
                # For this MVP, we are not handling 'model' role in input messages for Gemini,
                # as all our inputs are 'system' followed by 'user'.

            gemini_messages.append({"role": "user", "parts": [{"text": user_content}]})

            # For Gemini, JSON response format is set in generation_config
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4
            ) if response_format == "json_object" else genai.types.GenerationConfig(temperature=0.4)

            response = gemini_model.generate_content(
                gemini_messages, # Use the correctly formatted messages for Gemini
                generation_config=generation_config
            )
            return response.text
        else:
            raise ValueError(f"LLM choice '{llm_choice}' is not supported.")
    except Exception as e:
        print(f"Error calling LLM ({llm_choice}): {e}")
        # Return a JSON error if JSON format was expected, otherwise a text error
        return json.dumps({"error": str(e)}) if response_format == "json_object" else f"Error: {e}"


# --- AGENT 1: Data Extraction Agent ---
def data_extraction_agent_run(sow_text: str, llm_choice: str = "openai") -> dict:
    """
    Agent responsible for extracting structured information from raw SOW text.
    """
    if not sow_text:
        return {"error": "No SOW text provided for extraction."}

    sow_text_limited = sow_text[:15000] # Limit input to manage token costs

    system_instruction = "You are an expert AI assistant specialized in analyzing Scope of Work (SOW) documents. Provide precise JSON output."
    user_prompt = f"""
    Read the following SOW text carefully and extract the key information into a structured JSON object.
    Be precise and comprehensive. If a field is not explicitly mentioned or clearly derivable, return an empty array `[]` for lists, and "N/A" for single string fields. Do NOT return "N/A" for list fields.

    Prioritize finding the following specific details:
    - **Project Name:** (string) Look for explicit mentions like "Project Name:", "Title:", "Project Title:", "Subject:", or the main subject of the document. If not found, return "N/A".
    - **Client Name:** (string) Look for "Client:", "Customer:", "Issued By:", "For:", "Organization Name:" or the organization requesting the work. If not found, return "N/A".
    - **Timeline Overview:** (list of strings) Look for sections like "Project Schedule", "Timeline", "Duration", "Key Dates", or phrases indicating start/end dates, phases, or total duration (e.g., "6 months", "Phase 1: Q3 2025"). If not found, return `[]`.

    SOW Text:
    ---
    {sow_text_limited}
    ---

    Extract the following fields:
    - "project_name": (string) The official or implied name of the project.
    - "client_name": (string) The name of the client/organization issuing the SOW.
    - "objectives": (list of strings) A concise list of the main goals or aims of the project, as bullet points.
    - "scope_of_work": (list of strings) A detailed, bulleted summary of the activities, tasks, and responsibilities explicitly included.
    - "out_of_scope": (list of strings) A detailed, bulleted summary of activities, tasks, or responsibilities explicitly excluded.
    - "deliverables": (list of objects) A list of tangible outputs or results expected. Each item MUST be an object with "name" (string) and "description" (string) keys.
      Example: [{"name": "Final Report", "description": "Comprehensive project summary"}, {"name": "Software Module X", "description": "Developed and tested code"}]
    - "technical_requirements": (list of strings) A list of specific technologies, platforms, tools, standards, or methodologies mentioned.
    - "key_constraints": (list of strings) A list of any significant limitations, assumptions, risks, or conditions.
    - "stakeholders": (list of strings) A list of key roles, teams, or departments involved from both client and vendor sides.
    - "timeline_overview": (list of strings) A list of strings describing the project duration, phases, or key milestones.

    Return only the JSON object. Ensure the JSON is well-formed and valid. For any list field where no information is found, return an empty array `[]`. For any string field where no information is found, return "N/A".
    STRICTLY ADHERE TO THE SPECIFIED JSON SCHEMA.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    response_content = _call_llm(messages, response_format="json_object", llm_choice=llm_choice)
    try:
        parsed_data = json.loads(response_content)

        # --- Post-deserialization cleanup for list fields that might contain "N/A" or null ---
        # Helper to ensure a field is a list of strings, converting if necessary
        def ensure_list_of_strings(field_value):
            if isinstance(field_value, list):
                cleaned_list = [item for item in field_value if isinstance(item, str) and item.lower() != "n/a"]
                return cleaned_list
            elif isinstance(field_value, str) and field_value.lower() == "n/a":
                return []
            return []

        parsed_data["objectives"] = ensure_list_of_strings(parsed_data.get("objectives"))
        parsed_data["scope_of_work"] = ensure_list_of_strings(parsed_data.get("scope_of_work"))
        parsed_data["out_of_scope"] = ensure_list_of_strings(parsed_data.get("out_of_scope"))
        parsed_data["technical_requirements"] = ensure_list_of_strings(parsed_data.get("technical_requirements"))
        parsed_data["key_constraints"] = ensure_list_of_strings(parsed_data.get("key_constraints"))
        parsed_data["stakeholders"] = ensure_list_of_strings(parsed_data.get("stakeholders"))
        parsed_data["timeline_overview"] = ensure_list_of_strings(parsed_data.get("timeline_overview"))

        # Special handling for Deliverables (List of Maps)
        cleaned_deliverables = []
        raw_deliverables = parsed_data.get("deliverables")
        if isinstance(raw_deliverables, list):
            for item in raw_deliverables:
                if isinstance(item, dict) and "name" in item and "description" in item:
                    cleaned_deliverables.append(item)
                elif isinstance(item, str) and item.lower() != "n/a":
                    cleaned_deliverables.append({"name": item, "description": "Not detailed by AI"})
        parsed_data["deliverables"] = cleaned_deliverables

        # Basic validation for single string fields to ensure they are not null or empty
        if not parsed_data.get("project_name") or parsed_data.get("project_name").lower() == "n/a":
            parsed_data["project_name"] = "N/A"
        if not parsed_data.get("client_name") or parsed_data.get("client_name").lower() == "n/a":
            parsed_data["client_name"] = "N/A"

        return parsed_data
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from LLM: {response_content}")
        return {"error": "Failed to parse LLM response as JSON. Raw LLM output: " + response_content[:500]}
    except Exception as e:
        print(f"An unexpected error occurred during SOW analysis: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


# --- AGENT 2: Analysis Agent ---
def analysis_agent_run(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Agent responsible for generating a detailed natural language summary from structured SOW data.
    This acts as the primary "analysis" output for the MVP.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot summarize: Invalid or missing SOW structured data."

    sow_json_str = json.dumps(sow_structured_data, indent=2)

    system_instruction = "You are a professional technical writer and summarizer. Provide a detailed and well-structured summary."
    user_prompt = f"""
    Based on the following structured Scope of Work (SOW) data, generate a comprehensive and detailed natural language summary.
    The summary should be professional, concise, and highlight all critical aspects.
    Organize it logically with clear headings or bullet points where appropriate.
    Ensure all key information (Project Name, Client, Objectives, Scope, Deliverables, Technical Requirements, Constraints, Timeline) is covered.

    Structured SOW Data:
    ---
    {sow_json_str}
    ---

    Detailed Summary:
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)


# --- AGENT 3: Proposal Generation Agent ---
def proposal_generation_agent_run(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Agent responsible for generating a draft technical proposal based on structured SOW data.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot draft proposal: Invalid or missing SOW structured data."

    # Extracting data with fallbacks for cleaner prompt formatting
    projectName = sow_structured_data.get("project_name", "the Project")
    clientName = sow_structured_data.get("client_name", "the Client")
    objectives = format_list_for_prompt(sow_structured_data.get("objectives"), "To be defined based on client needs.")
    scopeOfWork = format_list_for_prompt(sow_structured_data.get("scope_of_work"), "Detailed scope will be outlined upon further analysis.")
    outOfScope = format_list_for_prompt(sow_structured_data.get("out_of_scope"), "Any items not explicitly included in the 'Scope of Work' are considered out of scope.")
    
    deliverablesBuilder = []
    if sow_structured_data.get("deliverables"):
        for d in sow_structured_data["deliverables"]:
            if isinstance(d, dict) and "name" in d and "description" in d:
                deliverablesBuilder.append(f"- **{d['name']}**: {d['description']}")
            elif isinstance(d, str): # Fallback for string deliverables
                deliverablesBuilder.append(f"- **{d}**: Not detailed by AI")
    deliverables = "\n" + "\n".join(deliverablesBuilder) if deliverablesBuilder else "- Specific deliverables to be detailed."


    technicalRequirements = sow_structured_data.get("technical_requirements")
    technicalRequirements_str = ", ".join(technicalRequirements) if technicalRequirements else "relevant technologies and industry best practices"

    keyConstraints = format_list_for_prompt(sow_structured_data.get("key_constraints"), "Standard project constraints apply.")
    stakeholders = sow_structured_data.get("stakeholders")
    stakeholders_str = ", ".join(stakeholders) if stakeholders else "key client and vendor personnel"

    timelineOverview = sow_structured_data.get("timeline_overview")
    timelineOverview_str = " ".join(timelineOverview) if timelineOverview else "A detailed project timeline will be developed in collaboration with the client."


    system_instruction = "You are an experienced technical proposal writer. Generate a comprehensive and professional technical proposal draft in Markdown format, directly addressing the SOW details. Be thorough and persuasive."
    user_prompt = f"""
    Based on the following extracted Scope of Work (SOW) details for "{projectName}" by "{clientName}",
    draft a comprehensive technical proposal. Use professional, persuasive language and standard Markdown formatting for readability.
    Ensure the proposal directly addresses the client's needs and clearly outlines our proposed solution.

    ---
    Extracted SOW Details:
    {json.dumps(sow_structured_data, indent=2)}
    ---

    # Technical Proposal for {projectName}

    ## 1. Executive Summary
    Provide a concise, high-level overview of {clientName}'s challenge, our understanding of {projectName}'s objectives, and how our solution will deliver value. Emphasize key benefits and our unique capabilities.

    ## 2. Understanding the Client's Needs & Objectives
    Demonstrate a clear understanding of {clientName}'s current situation and the specific problems or opportunities {projectName} aims to address.
    **Key Objectives:**
    {objectives}

    ## 3. Proposed Solution & Approach
    Detail our recommended technical solution and the strategic approach we will take to achieve the project objectives.
    Describe the methodology (e.g., Agile, Waterfall) and how it aligns with the project's nature.
    Address the technical requirements mentioned ({technicalRequirements_str}).
    Outline the general approach we will take to execute the scope of work.

    ## 4. Scope of Work (Our Understanding)
    Clearly define the activities, tasks, and responsibilities that are **included** in our proposed solution. This should align directly with the SOW.
    {scopeOfWork}

    ## 5. Out of Scope
    Clearly define what is **not included** in this proposal to manage expectations and avoid misunderstandings.
    {outOfScope}

    ## 6. Key Deliverables
    List the tangible outputs and results that will be provided at various stages of the project.
    {deliverables}

    ## 7. Technical Architecture & Stack
    Propose a high-level technical architecture and specify the primary technologies, platforms, and tools that will be utilized, directly aligning with the SOW's technical requirements and our proposed solution.

    ## 8. Project Timeline & Phases
    Provide a high-level proposed timeline with key phases and milestones.
    {timelineOverview_str}

    ## 9. Project Team & Governance
    Outline the proposed team structure, key roles, and how the project will be managed and governed to ensure successful delivery and effective communication with {stakeholders_str}.

    ## 10. Assumptions and Constraints
    List any critical assumptions made in preparing this proposal and reiterate key constraints from the SOW that will influence project execution.
    {keyConstraints}

    ## 11. Next Steps
    Outline the proposed next steps to move forward with {clientName} and initiate {projectName}.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)

# Helper to format lists for prompts, with a default message if list is empty
def format_list_for_prompt(items: list, default_message: str) -> str:
    """Formats a list of strings into a bulleted string for LLM prompt."""
    if not items:
        return default_message
    return "\n- " + "\n- ".join(items)