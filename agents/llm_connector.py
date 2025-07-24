# --- agents/llm_connector.py ---
# Handles LLM client initialization and the core _call_llm logic.

import os
import json
from openai import OpenAI
import google.generativeai as genai

# Global LLM client instances (initialized by app.py)
openai_client = None
gemini_model = None

def initialize_llm_clients(llm_choice: str):
    """
    Initializes the global LLM client instances based on the chosen provider.
    Called once by app.py at startup.
    """
    global openai_client, gemini_model

    if llm_choice == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            openai_client = OpenAI(api_key=api_key)
        else:
            raise ValueError("OpenAI API Key not found. Set OPENAI_API_KEY in .env.")
    elif llm_choice == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-1.5-pro'
        else:
            raise ValueError("Google Gemini API Key not found. Set GOOGLE_API_KEY in .env.")
    else:
        raise ValueError(f"Invalid LLM_CHOICE: '{llm_choice}'. Must be 'openai' or 'gemini'.")


def _call_llm(messages: list, response_format: str = "text", llm_choice: str = "openai") -> str:
    """
    Internal helper to call the chosen LLM (OpenAI or Gemini).
    Args:
        messages (list): A list of message dictionaries for the chat completion.
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
                raise ValueError("OpenAI client not initialized. Call initialize_llm_clients first.")
            response = openai_client.chat.completions.create(
                model="gpt-4o", # Using gpt-4o for better quality. Can use "gpt-3.5-turbo" for faster, cheaper, but less capable results
                messages=messages,
                response_format={"type": "json_object"} if response_format == "json_object" else None,
                temperature=0.4 # Lower temperature for more factual/less creative output
            )
            return response.choices[0].message.content
        elif llm_choice == "gemini":
            if not gemini_model:
                raise ValueError("Gemini model not initialized. Call initialize_llm_clients first.")

            gemini_messages = []
            user_content = ""
            for msg in messages:
                if msg["role"] == "system":
                    user_content += msg["content"] + "\n\n"
                elif msg["role"] == "user":
                    user_content += msg["content"]

            gemini_messages.append({"role": "user", "parts": [{"text": user_content}]})

            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4
            ) if response_format == "json_object" else genai.types.GenerationConfig(temperature=0.4)

            response = gemini_model.generate_content(
                gemini_messages,
                generation_config=generation_config
            )
            return response.text
        else:
            raise ValueError(f"LLM choice '{llm_choice}' is not supported.")
    except Exception as e:
        print(f"Error calling LLM ({llm_choice}): {e}")
        return json.dumps({"error": str(e)}) if response_format == "json_object" else f"Error: {e}"