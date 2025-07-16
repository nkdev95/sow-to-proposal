import os
import json
from openai import OpenAI
import google.generativeai as genai

# --- LLM Clients Initialization ---
# Ensure your API keys are set as environment variables (recommended)
# e.g., OPENAI_API_KEY="sk-..." or GOOGLE_API_KEY="AIza..."

# OpenAI Client
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Gemini Client
gemini_model = None
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-1.5-pro'

def _call_llm(messages: list, response_format: str = "text", llm_choice: str = "openai") -> str:
    """
    Internal helper to call the chosen LLM.
    response_format can be "text" or "json_object"
    """
    try:
        if llm_choice == "openai" and openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o", # You can try "gpt-3.5-turbo" for faster, cheaper, but less capable results
                messages=messages,
                response_format={"type": "json_object"} if response_format == "json_object" else None
            )
            return response.choices[0].message.content
        elif llm_choice == "gemini" and gemini_model:
            # Gemini's JSON mode is different. It relies on the prompt and system instructions.
            # We explicitly ask for JSON in the prompt for Gemini.
            response = gemini_model.generate_content(
                messages,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json") if response_format == "json_object" else None
            )
            return response.text
        else:
            raise ValueError(f"LLM choice '{llm_choice}' is not supported or client not initialized.")
    except Exception as e:
        print(f"Error calling LLM ({llm_choice}): {e}")
        return json.dumps({"error": str(e)}) if response_format == "json_object" else f"Error: {e}"


def analyze_sow_structured(sow_text: str, llm_choice: str = "openai") -> dict:
    """
    Analyzes SOW text to extract structured information using an LLM.
    """
    if not sow_text:
        return {"error": "No SOW text provided for analysis."}

    prompt = f"""
    You are an expert AI assistant specialized in analyzing Scope of Work (SOW) documents.
    Read the following SOW text carefully and extract the key information into a structured JSON object.
    Be precise and comprehensive. If a field is not explicitly mentioned, indicate "N/A" or leave the list empty.

    SOW Text:
    ---
    {sow_text[:15000]} # Limit input to avoid token limits for very long docs
    ---

    Extract the following fields:
    - "project_name": The official or implied name of the project.
    - "client_name": The name of the client/organization issuing the SOW.
    - "objectives": A concise list of the main goals or aims of the project.
    - "scope_of_work": A detailed, bulleted summary of the activities, tasks, and responsibilities explicitly included.
    - "out_of_scope": A detailed, bulleted summary of activities, tasks, or responsibilities explicitly excluded.
    - "deliverables": A detailed list of the tangible outputs or results expected, with brief descriptions.
    - "technical_requirements": A list of specific technologies, platforms, tools, standards, or methodologies mentioned.
    - "key_constraints": A list of any significant limitations, assumptions, risks, or conditions.
    - "stakeholders": A list of key roles, teams, or departments involved from both client and vendor sides.
    - "timeline_overview": A high-level description of the project duration, phases, or key milestones.

    Return only the JSON object.
    """
    messages = [
        {"role": "system", "content": "You are an expert SOW analyst. Provide precise JSON output."},
        {"role": "user", "content": prompt}
    ]

    response_content = _call_llm(messages, response_format="json_object", llm_choice=llm_choice)
    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from LLM: {response_content}")
        return {"error": "Failed to parse LLM response as JSON."}

def summarize_sow_detailed(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Generates a detailed natural language summary from structured SOW data.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot summarize: Invalid or missing SOW structured data."

    sow_json_str = json.dumps(sow_structured_data, indent=2)

    prompt = f"""
    Based on the following structured Scope of Work (SOW) data, generate a comprehensive and detailed natural language summary.
    The summary should be professional, concise, and highlight all critical aspects.
    Organize it logically with clear headings or bullet points where appropriate.

    Structured SOW Data:
    ---
    {sow_json_str}
    ---

    Detailed Summary:
    """
    messages = [
        {"role": "system", "content": "You are a professional technical writer and summarizer."},
        {"role": "user", "content": prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)


def draft_technical_proposal(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Generates a draft technical proposal based on structured SOW data.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot draft proposal: Invalid or missing SOW structured data."

    project_name = sow_structured_data.get("project_name", "the Project")
    client_name = sow_structured_data.get("client_name", "the Client")
    objectives = "\\n- " + "\\n- ".join(sow_structured_data.get("objectives", ["To be defined"]))
    scope = "\\n- " + "\\n- ".join(sow_structured_data.get("scope_of_work", ["Detailed scope will be defined."]))
    deliverables = "\\n- " + "\\n- ".join([f"{d.get('name', 'N/A')}: {d.get('description', 'N/A')}" for d in sow_structured_data.get("deliverables", [])])
    tech_reqs = ", ".join(sow_structured_data.get("technical_requirements", ["various technologies"]))
    constraints = "\\n- " + "\\n- ".join(sow_structured_data.get("key_constraints", ["Standard project constraints apply."]))
    timeline = sow_structured_data.get("timeline_overview", "A detailed timeline will be developed.")

    # Main prompt for generating the technical proposal.
    # This is highly simplified for an MVP. For production, you'd have more sections
    # and potentially separate LLM calls for each section, chained together.
    prompt = f"""
    Based on the following extracted Scope of Work (SOW) details for "{project_name}" by "{client_name}",
    draft a technical proposal. Use professional language and standard proposal formatting (Markdown).

    ---
    Extracted SOW Details:
    {json.dumps(sow_structured_data, indent=2)}
    ---

    ## 1. Executive Summary
    Provide a concise overview of the project, the client's needs, and our proposed solution.

    ## 2. Problem Statement
    Summarize the key challenges or needs that {client_name} is facing, as implied or stated in the SOW.

    ## 3. Proposed Solution & Approach
    Describe our recommended technical solution and methodology to achieve the project objectives.
    Address the technical requirements mentioned ({tech_reqs}).
    Outline the general approach we will take to execute the scope of work.

    ## 4. Scope of Work (As Understood)
    Based on the SOW, reiterate the key activities and responsibilities included in this project.
    {scope}

    ## 5. Key Deliverables
    List the tangible outputs and results that will be provided by our team.
    {deliverables}

    ## 6. Technical Architecture & Stack
    Propose a high-level technical architecture and primary technologies that will be utilized, aligning with the SOW's technical requirements.

    ## 7. Project Timeline & Phases
    Provide a high-level proposed timeline and key project phases based on the SOW's {timeline}.

    ## 8. Team & Governance (Placeholder)
    Briefly mention the type of team structure and governance that would be applied.

    ## 9. Assumptions and Constraints
    List any critical assumptions made and reiterate key constraints from the SOW.
    {constraints}

    """
    messages = [
        {"role": "system", "content": "You are an experienced technical proposal writer. Generate a comprehensive draft in Markdown format."},
        {"role": "user", "content": prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)