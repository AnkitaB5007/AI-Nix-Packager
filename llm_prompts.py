# llm_prompts.py

def build_prompt(default_nix_content: str, error_message: str) -> str:
    """
    Build the structured prompt for fixing Nix expressions.
    
    Args:
        default_nix_content (str): Contents of the broken default.nix file.
        error_message (str): Error message captured from nix-build.

    Returns:
        str: A formatted prompt string.
    """
    prompt = f"""
    You are an **expert NixOS/Nixpkgs contributor** with deep expertise in writing and fixing Nix expressions for Python packages. 
    You have authored hundreds of production-ready `default.nix` files.
    
    You have been given:
    1. The complete contents of current broken `default.nix` file.
    2. The latest compilation error from `nix-build`.
    
    ## Current Nix file content:
    ```nix
    {default_nix_content}
    ```
    
    ## Current error message:
    ```
    {error_message}
    ```
    ### INSTRUCTIONS:
    - Identify the cause of the compilation error using the given context.
    - Correct the `default.nix` file so that it will successfully build.
    - Ensure the fix is different from past failed attempts.

    Return ONLY valid, complete JSON with exactly these two keys:
    1. "corrected_nix_code": Corrected nix code content,
    2. "explanation": Keep explanations brief to avoid truncation.
    """
    return prompt
