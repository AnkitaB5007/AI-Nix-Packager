import re
import json
import subprocess

# Regex from https://stackoverflow.com/a/14693789
# This pattern matches ANSI escape sequences used for terminal colors and formatting
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def parse_error_from_nix_output(output):
    """
    Parse and extract error messages from Nix build output.
    
    Args:
        output: Raw output from Nix containing JSON-formatted log messages
        
    Returns:
        str: A single cleaned error message
        
    Raises:
        AssertionError: If output format is unexpected or number of errors != 1
    """
    error_messages = []
    
    # Process each line of the Nix output
    for line in output.split("\n"):
        # Skip empty lines
        if line == "":
            continue
            
        # Each line should start with "@nix " prefix (Nix's structured logging format)
        prefix = "@nix "
        assert line.startswith(prefix), f"Line does not start with @nix : {line}"
        
        # Remove the prefix to get the JSON content
        line = line.lstrip(prefix)
        
        # Parse the JSON content of the log line
        parsed = json.loads(line)
        assert "action" in parsed, f"Nix JSON output does not have an action key: {parsed}"
        
        # Only process lines that are actual messages (not other action types)
        if parsed["action"] != "msg":
            continue
            
        # Ensure the message has content
        assert "msg" in parsed, f"Nix JSON output does not have a msg key: {parsed}"
        
        # Skip progress messages about fetching inputs (these aren't errors)
        if parsed["msg"].startswith("fetching path input "):
            continue
            
        # Extract the error message (prefer raw_msg if available)
        if "raw_msg" in parsed:
            error_message = parsed["raw_msg"]
            
            # Check if the error message contains a reference to a derivation log
            # Pattern matches "nix log /nix/store/..." in the error message
            derivation_path_search = re.search(r'nix log (/nix/store/.*\.drv)', error_message)
            if derivation_path_search:
                # Extract the derivation path and get detailed build logs
                derivation_path = derivation_path_search.group(1)
                # TODO: teach nix log to respect the NO_COLOR environment variable
                error_message = subprocess.run(("nix", "log", derivation_path), capture_output=True, encoding='utf-8', check=True).stdout
            
            # Remove ANSI escape codes (colors, formatting) from the error message
            error_message = ansi_escape.sub('', error_message)
            error_messages.append(error_message)
    
    # Validate that we found exactly one error message
    num_error_messages = len(error_messages)
    assert num_error_messages == 1, f"Unexpected number of error messages. Expected 1, found {num_error_messages}, output: {output}"
    
    # Return the single cleaned error message
    return error_messages[0]