import random
import logging



# Simply delete a random line
# TODO: use a smarter strategy
def execute(code):
    logger = logging.getLogger(__name__)

    def should_line_be_deleted(line):
        do_not_delete_set = set((
            " hash = ",
            " name = ",
            " pname = ",
            " version = ",
            " src = ",
            " owner = ",
            " repo = "
            " tag = ",
            " rev = ",
            " doCheck = ",
            " meta = ",
            " description = ",
            " homepage = ",
            " license = ",
            " maintainers = ",
        ))
        for do_not_delete_str in do_not_delete_set:
            if do_not_delete_str in line:
                logger.info(f'Line "{line}" should not be deleted, skipping')
                return False
        return True

    max_attempts = 500
    for _ in range(max_attempts):
        lines = code.split("\n") # splitlines() would remove empty lines at the end
        line_count = len(lines)
        line_number = random.randrange(0, line_count)
        line = lines[line_number]
        if not should_line_be_deleted(line):
            continue
        del lines[line_number]
        return "\n".join(lines)
    else:
        raise Exception(f"Could not find a suitable line to delete after {max_attempts} attempts")
