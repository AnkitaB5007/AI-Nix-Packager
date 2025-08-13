import re
import json
import subprocess

# Regex from https://stackoverflow.com/a/14693789
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def parse_error_from_nix_output(output):
    error_messages = []
    for line in output.split("\n"):
        if line == "":
            continue
        prefix = "@nix "
        assert line.startswith(prefix), f"Line does not start with @nix : {line}"
        line = line.lstrip(prefix)
        parsed = json.loads(line)
        assert "action" in parsed, f"Nix JSON output does not have an action key: {parsed}"
        if parsed["action"] != "msg":
            continue
        assert "msg" in parsed, f"Nix JSON output does not have a msg key: {parsed}"
        if parsed["msg"].startswith("fetching path input "):
            continue
        if "raw_msg" in parsed:
            error_message = parsed["raw_msg"]
            derivation_path_search = re.search('For full logs, run:\n  nix log (/nix/store/.*.drv)', error_message)
            if derivation_path_search:
                derivation_path = derivation_path_search.group(1)
                # TODO: teach nix log to respect the NO_COLOR environment variable
                error_message = subprocess.run(("nix", "log", derivation_path), capture_output=True, encoding='utf-8', check=True).stdout
            error_message = ansi_escape.sub('', error_message)
            error_messages.append(error_message)
    num_error_messages = len(error_messages)
    assert num_error_messages == 1, f"Unexpected number of error messages. Expected 1, found {num_error_messages}"
    return error_messages[0]
