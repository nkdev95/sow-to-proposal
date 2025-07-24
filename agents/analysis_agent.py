# --- agents/analysis_agent.py ---
# Agent responsible for generating a detailed natural language summary from structured SOW data.

import json
from agents.llm_connector import _call_llm # Import the shared LLM caller

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