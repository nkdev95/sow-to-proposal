# --- agents/proposal_generation_agent.py ---
# Agent responsible for generating a draft technical proposal based on structured SOW data.

import json
from agents.llm_connector import _call_llm # Import the shared LLM caller

# Helper to format lists for prompts, with a default message if list is empty
def _format_list_for_prompt(items: list, default_message: str) -> str:
    """Formats a list of strings into a bulleted string for LLM prompt."""
    if not items:
        return default_message
    return "\n- " + "\n- ".join(items)


def proposal_generation_agent_run(sow_structured_data: dict, llm_choice: str = "openai") -> str:
    """
    Agent responsible for generating a draft technical proposal based on structured SOW data.
    """
    if not sow_structured_data or sow_structured_data.get("error"):
        return "Cannot draft proposal: Invalid or missing SOW structured data."

    # Extracting data with fallbacks for cleaner prompt formatting
    projectName = sow_structured_data.get("project_name", "the Project")
    clientName = sow_structured_data.get("client_name", "the Client")
    objectives = _format_list_for_prompt(sow_structured_data.get("objectives"), "To be defined based on client needs.")
    scopeOfWork = _format_list_for_prompt(sow_structured_data.get("scope_of_work"), "Detailed scope will be outlined upon further analysis.")
    outOfScope = _format_list_for_prompt(sow_structured_data.get("out_of_scope"), "Any items not explicitly included in the 'Scope of Work' are considered out of scope.")
    
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

    keyConstraints = _format_list_for_prompt(sow_structured_data.get("key_constraints"), "Standard project constraints apply.")
    stakeholders = sow_structured_data.get("stakeholders")
    stakeholders_str = ", ".join(stakeholders) if stakeholders else "key client and vendor personnel"

    timelineOverview = sow_structured_data.get("timeline_overview")
    timelineOverview_str = " ".join(timelineOverview) if timelineOverview else "A detailed project timeline will be developed in collaboration with the client."


    system_instruction = "You are a senior solution architect and expert technical proposal writer. Your task is to generate a comprehensive, persuasive, and professional technical proposal draft in Markdown format. The proposal must directly address the client's Scope of Work details and clearly outline our proposed solution."
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
    Provide a concise, high-level overview of {clientName}'s challenge, our understanding of {projectName}'s objectives, and how our solution will deliver value. Emphasize key benefits and our unique capabilities. This section should compel the reader to continue.

    ## 2. Understanding the Client's Needs & Objectives
    Demonstrate a clear and empathetic understanding of {clientName}'s current situation, their stated and implied pain points, and the specific problems or opportunities {projectName} aims to address. Clearly articulate how our understanding aligns with their vision.
    **Key Objectives:**
    {objectives}

    ## 3. Proposed Solution & Approach
    Detail our recommended technical solution, outlining its core components and how it directly addresses the client's objectives and technical requirements. Describe the strategic approach and methodology (e.g., Agile, phased implementation, iterative development) we will employ to achieve project success.
    Address the technical requirements mentioned ({technicalRequirements_str}) by explaining how our solution incorporates or leverages them.

    ## 4. Scope of Work (Our Understanding)
    Clearly define the activities, tasks, and responsibilities that are **included** in our proposed solution. This should align precisely with the SOW, ensuring no ambiguity.
    {scopeOfWork}

    ## 5. Out of Scope
    Clearly define what is **not included** in this proposal to manage expectations, prevent scope creep, and avoid misunderstandings.
    {outOfScope}

    ## 6. Key Deliverables
    List the tangible outputs and results that will be provided at various stages of the project. For each deliverable, briefly describe its purpose or content.
    {deliverables}

    ## 7. Technical Architecture & Stack
    Propose a high-level technical architecture diagram (described in text) and specify the primary technologies, platforms, and tools that will be utilized. Explain how this stack aligns with the SOW's technical requirements, ensures scalability, security, and performance.

    ## 8. Project Timeline & Phases
    Provide a high-level proposed timeline with key phases and milestones. Describe the duration of each phase and what will be achieved.
    {timelineOverview_str}

    ## 9. Project Team & Governance
    Outline the proposed team structure, key roles (e.g., Project Manager, Lead Developer, QA), and how the project will be managed and governed. Describe communication protocols and reporting mechanisms to ensure successful delivery and effective collaboration with {stakeholders_str}.

    ## 10. Assumptions and Constraints
    List any critical assumptions made in preparing this proposal (e.g., client data availability, access to systems) and reiterate key constraints from the SOW (e.g., budget limits, specific regulatory requirements) that will influence project execution.

    ## 11. Next Steps
    Outline the proposed next steps to move forward with {clientName} and initiate {projectName}. This should include any necessary meetings, approvals, or detailed planning sessions.
    """
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    return _call_llm(messages, response_format="text", llm_choice=llm_choice)