# --- llm_agents.py ---
# This file contains the core AI agent logic for SOW analysis, summarization,
# and technical proposal drafting, interacting with the chosen LLM.

import os
import json
from openai import OpenAI
import google.generativeai as genai

# --- LLM Clients Initialization (Placeholders) ---
# These clients will be initialized by app.py based on user's LLM_CHOICE and API key availability.
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
                model="gpt-4o", # Using gpt-4o for better quality. Can use "gpt-3.5-turbo" for speed/cost.
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


def analyze_sow_structured(sow_text: str, llm_choice: str = "openai") -> dict:
    """
    Analyzes SOW text to extract structured information using an LLM.
    Args:
        sow_text (str): The full text content of the SOW document.
        llm_choice (str): The chosen LLM provider ("openai" or "gemini").
    Returns:
        dict: A dictionary containing the structured SOW data or an error message.
    """
    if not sow_text:
        return {"error": "No SOW text provided for analysis."}

    # Limit input text to manage token costs and context window limits for very long documents
    # Adjust this limit based on your chosen LLM's context window and cost considerations.
    # 15000 characters is a rough estimate, actual token count varies.
    sow_text_limited = sow_text[:15000]

    system_instruction = "You are an expert AI assistant specialized in analyzing Scope of Work (SOW) documents. Provide precise JSON output."
    user_prompt = f"""
    Read the following SOW text carefully and extract the key information into a structured JSON object.
    Be precise and comprehensive. If a field is not explicitly mentioned or clearly derivable, indicate "N/A" or leave the list empty.

    SOW Text:
    ---
    {sow_text_limited}
    ---

    Extract the following fields:
    - "project_name": The official or implied name of the project.
    - "client_name": The name of the client/organization issuing the SOW.
    - "objectives": A concise list of the main goals or aims of the project, as bullet points.
    - "scope_of_work": A detailed, bulleted summary of the activities, tasks, and responsibilities explicitly included.
    - "out_of_scope": A detailed, bulleted summary of activities, tasks, or responsibilities explicitly excluded.
    - "deliverables": A list of tangible outputs or results expected. Each item should be an object with "name" and "description".
    - "technical_requirements": A list of specific technologies, platforms, tools, standards, or methodologies mentioned.
    - "key_constraints": A list of any significant limitations, assumptions, risks, or conditions.
    - "stakeholders": A list of key roles, teams, or departments involved from both client and vendor sides.
    - "timeline_overview": A high-level description of the project duration, phases, or key milestones.

    Return only the JSON object. Ensure the JSON is well-formed and valid.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    response_content = _call_llm(messages, response_format="json_object", llm_choice=llm_choice)
    try:
        parsed_data = json.loads(response_content)
        # Basic validation to ensure expected keys are present, even if empty/N/A
        expected_keys = ["project_name", "client_name", "objectives", "scope_of_work",
                         "out_of_scope", "deliverables", "technical_requirements",
                         "key_constraints", "stakeholders", "timeline_overview"]
        for key in expected_keys:
            if key not in parsed_data:
                parsed_data[key] = "N/A" if key in ["project_name", "client_name", "timeline_overview"] else []
        return parsed_data
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from LLM: {response_content}")
        return {"error": "Failed to parse LLM response as JSON. Raw LLM output: " + response_content[:500]}
    except Exception as e:
        print(f"An unexpected error occurred during SOW analysis: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


def summarize_sow_detailed(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Generates a detailed natural language summary from structured SOW data.
    Args:
        sow_structured_data (dict): The structured SOW data (output from analyze_sow_structured).
        llm_choice (str): The chosen LLM provider ("openai" or "gemini").
    Returns:
        str: A comprehensive natural language summary of the SOW.
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


def draft_technical_proposal(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Generates a draft technical proposal based on structured SOW data.
    Args:
        sow_structured_data (dict): The structured SOW data (output from analyze_sow_structured).
        llm_choice (str): The chosen LLM provider ("openai" or "gemini").
    Returns:
        str: A draft technical proposal in Markdown format.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot draft proposal: Invalid or missing SOW structured data."

    # Extracting data with fallbacks for cleaner prompt formatting
    project_name = sow_structured_data.get("project_name", "the Project")
    client_name = sow_structured_data.get("client_name", "the Client")
    objectives = "\\n- " + "\\n- ".join(sow_structured_data.get("objectives", ["To be defined based on client needs."]))
    scope_of_work = "\\n- " + "\\n- ".join(sow_structured_data.get("scope_of_work", ["Detailed scope will be outlined upon further analysis."]))
    out_of_scope = "\\n- " + "\\n- ".join(sow_structured_data.get("out_of_scope", ["Any items not explicitly included in the 'Scope of Work' are considered out of scope."]))
    
    deliverables_list = []
    for d in sow_structured_data.get("deliverables", []):
        deliverables_list.append(f"- **{d.get('name', 'N/A')}**: {d.get('description', 'N/A')}")
    deliverables = "\\n" + "\\n".join(deliverables_list) if deliverables_list else "- Specific deliverables to be detailed."

    technical_requirements = ", ".join(sow_structured_data.get("technical_requirements", ["relevant technologies and industry best practices"]))
    key_constraints = "\\n- " + "\\n- ".join(sow_structured_data.get("key_constraints", ["Standard project constraints apply."]))
    stakeholders = ", ".join(sow_structured_data.get("stakeholders", ["key client and vendor personnel"]))
    timeline_overview = sow_structured_data.get("timeline_overview", "A detailed project timeline will be developed in collaboration with the client.")

    system_instruction = "You are an experienced technical proposal writer. Generate a comprehensive and professional technical proposal draft in Markdown format, directly addressing the SOW details. Be thorough and persuasive."
    user_prompt = f"""
    Based on the following extracted Scope of Work (SOW) details for "{project_name}" by "{client_name}",
    draft a comprehensive technical proposal. Use professional, persuasive language and standard Markdown formatting for readability.
    Ensure the proposal directly addresses the client's needs and clearly outlines our proposed solution.

    ---
    Extracted SOW Details:
    {json.dumps(sow_structured_data, indent=2)}
    ---

    # Technical Proposal for {project_name}

    ## 1. Executive Summary
    Provide a concise, high-level overview of {client_name}'s challenge, our understanding of {project_name}'s objectives, and how our solution will deliver value. Emphasize key benefits and our unique capabilities.

    ## 2. Understanding the Client's Needs & Objectives
    Demonstrate a clear understanding of {client_name}'s current situation and the specific problems or opportunities {project_name} aims to address.
    **Key Objectives:**
    {objectives}

    ## 3. Proposed Solution & Approach
    Detail our recommended technical solution and the strategic approach we will take to achieve the project objectives.
    Describe the methodology (e.g., Agile, Waterfall) and how it aligns with the project's nature.
    Address the technical requirements mentioned ({technical_requirements}).
    Outline the general approach we will take to execute the scope of work.

    ## 4. Scope of Work (Our Understanding)
    Clearly define the activities, tasks, and responsibilities that are **included** in our proposed solution. This should align directly with the SOW.
    {scope_of_work}

    ## 5. Out of Scope
    Clearly define what is **not included** in this proposal to manage expectations and avoid misunderstandings.
    {out_of_scope}

    ## 6. Key Deliverables
    List the tangible outputs and results that will be provided at various stages of the project.
    {deliverables}

    ## 7. Technical Architecture & Stack
    Propose a high-level technical architecture and specify the primary technologies, platforms, and tools that will be utilized, directly aligning with the SOW's technical requirements and our proposed solution.

    ## 8. Project Timeline & Phases
    Provide a high-level proposed timeline with key phases and milestones.
    {timeline_overview}

    ## 9. Project Team & Governance
    Outline the proposed team structure, key roles, and how the project will be managed and governed to ensure successful delivery and effective communication with {stakeholders}.

    ## 10. Assumptions and Constraints
    List any critical assumptions made in preparing this proposal and reiterate key constraints from the SOW that will influence project execution.
    {key_constraints}

    ## 11. Next Steps
    Outline the proposed next steps to move forward with {client_name} and initiate {project_name}.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)