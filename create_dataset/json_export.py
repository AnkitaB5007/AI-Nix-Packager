import jsonlines
import create_dataset.utils as utils
from tqdm import tqdm

if __name__ == '__main__':
    db = utils.DB("create_dataset/dataset.db")
    with jsonlines.open('create_dataset/export.jsonl', mode='w') as writer:
        for row in tqdm(db.read_from_dataset()):
            (id_, pname, attribute_name, system, file, nixpkgs_revision, code_breaking_algorithm, nix_code_working, nix_code_broken, error_message, compile_time_s) = row
            row = {
                "pname": pname,
                "attribute_name": attribute_name,
                "system": system,
                "file": file,
                "nixpkgs_revision": nixpkgs_revision,
                "code_breaking_algorithm": code_breaking_algorithm,
                "nix_code_working": nix_code_working,
                "nix_code_broken": nix_code_broken,
                "error_message": error_message,
                "compile_time_s": compile_time_s,
            }
            writer.write(row)

# TODO:
# - Reduce the amout of examples with syntax errors
# - If a single file is being edited many times, perhaps the file path is not accurate and we should ignore this
# - grep the error messages to see if any network errors made it into the logs
