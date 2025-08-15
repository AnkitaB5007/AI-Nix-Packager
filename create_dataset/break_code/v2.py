import random
import logging


# I'm sure this code is full of bugs due to not using a proper parser but rolling our own.
# For example, the code does not handle multi-line comments.
# Oh well, for this dataset it's probably good enough for now.

# TODO: use a proper parser and a better deletion strategy


# Simply delete a random function argument
def execute(code):
    logger = logging.getLogger(__name__)

    # TODO: use a proper Nix parsing library line rnix to properly parse the code
    # TODO: handle comments
    def extract_dependencies(code):
        start_of_arguments_parts = code.split("{", 1)
        assert len(start_of_arguments_parts) == 2, "Nix code does not have an opening curly brace"
        start_of_arguments = start_of_arguments_parts[1]
        function_argument_parts = start_of_arguments.split("}", 1)
        assert len(function_argument_parts) == 2, "Nix code does not have a closing curly brace after an opening one"
        function_arguments_str = function_argument_parts[0]
        function_arguments_with_whitespace = function_arguments_str.split(",")
        function_arguments_maybe_option = set(map(str.strip, function_arguments_with_whitespace))

        def remove_option(s):
            return s.split("?")[0].strip()
        function_arguments_maybe_comment = set(map(remove_option, function_arguments_maybe_option))

        def remove_line_comment(s):
            return s.split("#")[0].strip()
        function_arguments_maybe_empty = set(map(remove_line_comment, function_arguments_maybe_comment))
        function_arguments = set(filter(None, function_arguments_maybe_empty))
        return function_arguments

    dependencies = extract_dependencies(code)
    logger.debug(f"dependencies: {dependencies}")
    while True:
        if len(dependencies) <= 0:
            raise Exception("No suitable dependency found for deletion")

        random_dependency = random.choice(tuple(dependencies))
        logger.debug(f"random_dependency: {random_dependency}")
        dependencies.remove(random_dependency) # Remember that we removed this element for future loop iterations

        do_not_delete_set = set((
            "...",
            "lib",
            "pkgs",
            "stdenv",
            "buildPythonPackage",
            "callPackage",
            "isPy3k",
        ))
        if random_dependency in do_not_delete_set or "fetch" in random_dependency:
            logger.info(f'Function input "{random_dependency}" should not be deleted, skipping')
            continue
        else:
            break

    def delete_function_argument(code):
        lines = code.split("\n") # splitlines() would remove empty lines at the end
        def filter_function(line):
            if f"{random_dependency}," in line:
                return False
            if f", {random_dependency}" in line:
                return False
            if f",  {random_dependency}" in line:
                return False
            if f"{random_dependency} ?" in line:
                return False
            if f"{random_dependency}?" in line:
                return False
            return True
        lines = filter(filter_function, lines)
        return "\n".join(lines)

    def delete_in_lists(code):
        lines_before = code.split("\n") # splitlines() would remove empty lines at the end
        def filter_function(line):
            if line.strip() == random_dependency:
                return False
            return True
        lines_after = list(filter(filter_function, lines_before))
        if lines_before != lines_after:
            return "\n".join(lines_after)
        # Did not find and delete anything
        code_after = code.replace(f"{random_dependency} ", "")
        if code_after == code: # Did not find anything again
            # Brute-force method
            code_after = code.replace(random_dependency, "")
        return code_after

    code = delete_function_argument(code) # Try to find the dependency in the function arguments
    code = delete_in_lists(code) # Try to find the dependency in lists like buildInputs
    return code
