import os
import requests, json
from llm_prompts import build_prompt
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, Union, List
load_dotenv()

# --- 1. Define Pydantic Models for structured data ---
# Define the model for the LLM's response.
# This helps ensure the LLM's output is consistently parsable.
class NixFixResponse(BaseModel):
    corrected_nix_code: str
    explanation: Optional[str] = "No explanation provided."


# 1. Define schema
class FixResponse(BaseModel):
    corrected_nix_code: str
    explanation: Union[str, List[str]]

print("Pydantic models defined.")

load_dotenv()
API_KEY = os.getenv("RUNPOD_API_KEY")
API_URL = os.getenv("RUNPOD_ENDPOINT")

HEADERS = {
    "accept": "application/json",
    "authorization": API_KEY,
    "content-type": "application/json",
}



def get_llm_fix(default_nix_content: str, error_message: str, error_history=None) -> Optional[NixFixResponse]:
    """
    Sends the Nix file and error message to the Ollama model for a fix.
    """
    # Prepare history for the prompt
    history_text = "\n".join(
        f"- Error: {err}\n  Fix applied:\n{fix}"
        for err, fix in error_history
    ) if error_history else "None"
    prompt = build_prompt(default_nix_content, error_message)
    payload = {
        "input": {
            "prompt": prompt
        }
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
        resp.raise_for_status()
        print("Response received from RunPod API.", resp.status_code)
        data = resp.json()
        print("Response data:", data)

        # RunPod returns output as a list structure
        output_data = data.get("output", [])
        if not output_data:
            print("⚠️ No output in response:", data)
            return None

        # Extract the actual content - it's nested deep in the response
        try:
            # Navigate: output[0] -> choices[0] -> tokens[0]
            raw_content = output_data[0]['choices'][0]['tokens'][0]
            print("Raw content from API:", raw_content[:200], "...")
            
            # The content has both text and JSON - just get everything after the first {
            json_start = raw_content.find('{')
            if json_start == -1:
                print("⚠️ No JSON found in response")
                return None
            
            # Get everything from the first { onwards
            json_part = raw_content[json_start:]
            parsed = json.loads(json_part)
            
            # Handle explanation field - it could be a string or list
            explanation = parsed.get("explanation", "No explanation provided.")
            if isinstance(explanation, list):
                explanation = " ".join(explanation)
            
            return NixFixResponse(
                corrected_nix_code=parsed["corrected_nix_code"],
                explanation=explanation
            )
            FixResponse
        except (IndexError, KeyError) as e:
            print(f"⚠️ Error accessing RunPod response structure: {e}")
            print(f"Full response structure: {data}")
            return None
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            print(f"Attempted to parse: {json_part[:300]}...")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error during parsing: {e}")
            return None

    except Exception as e:
        print("❌ Error calling RunPod API:", e)
        return None