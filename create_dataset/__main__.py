# Run from the root of this repository with:
# python3 -m create_dataset
# But first adjust some variables in the code below like max_dataset_entries_to_create and nixpkgs_worktrees.
# You may also use fewer (or more) Nixpkgs checkouts. The number of parallel jobs scales with the number of Nixpkgs checkouts.
# To create a Nixpkgs checkout:
# - Clone Nixpkgs from https://github.com/NixOS/nixpkgs
# - Switch to a branch that is in the official cache: git checkout origin/nixos-unstable
# - Add a worktree: git worktree add ../nixpkgs2
# - Add as many worktrees as you like with the previous command

import os
import utils as common_utils
import random
import logging
import traceback
import multiprocessing
import create_dataset.utils as utils
import create_dataset.break_code.v1 as break_code_v1
import create_dataset.break_code.v2 as break_code_v2
from multiprocessing import Pool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s')

max_dataset_entries_to_create = 3000

nixpkgs_worktrees = [
    "../nixpkgs2",
    "../nixpkgs3",
    "../nixpkgs4",
    "../nixpkgs5",
    "../nixpkgs6",
    "../nixpkgs7",
    "../nixpkgs8",
    "../nixpkgs9",
    "../nixpkgs10",
    "../nixpkgs11",
]
assert sorted(set(nixpkgs_worktrees)) == sorted(nixpkgs_worktrees), "There are duplicate items in nixpkgs_worktrees"
nixpkgs_worktrees_abs = tuple(map(os.path.abspath, nixpkgs_worktrees))
assert sorted(set(nixpkgs_worktrees_abs)) == sorted(nixpkgs_worktrees_abs), "There are duplicate items in nixpkgs_worktrees after converting the paths to an absolute path"
print(f"WARNING: These worktrees will be modified: {nixpkgs_worktrees_abs}")
print("Make sure there are no changes you don't want to loose!")


db = utils.DB("create_dataset/dataset.db")


def check_all_worktrees_in_sync():
    print("Checking that all worktrees are in sync...")
    nixpkgs_rev = None
    for worktree in nixpkgs_worktrees:
        nixpkgs_rev_2 = utils.read_nixpkgs_rev(worktree)
        if nixpkgs_rev is None:
            nixpkgs_rev = nixpkgs_rev_2
        else:
            assert nixpkgs_rev == nixpkgs_rev_2, f"All Nixpkgs checkouts need to be on the same commit but {nixpkgs_worktrees[0]} is on commit {nixpkgs_rev}, while {worktree} is on {nixpkgs_rev_2}"
        print(f"{worktree} checked")
    return nixpkgs_rev

nixpkgs_rev_str = check_all_worktrees_in_sync()
nixpkgs_rev_bin = utils.nixpkgs_rev_str_to_bin(nixpkgs_rev_str)


packages = utils.get_all_pkgs_cached(db, nixpkgs_rev_bin, nixpkgs_worktrees[0])

package_list = tuple(packages.keys()) # tuple() is needed because random.choice() cannot handle dict_keys
packages_metadata = []
for i in range(max_dataset_entries_to_create):
    random_package_attr = random.choice(package_list)

    # To experiment with a specific package:
    #random_package_attr = "package_sttribute_here"

    package_metadata = utils.extract_metadata(nixpkgs_worktrees[0], random_package_attr, packages[random_package_attr])
    if package_metadata:
        packages_metadata.append(package_metadata)

print(f"{len(packages_metadata)} packages selected")


def collect_one_sample(package_metadata):
    logger = multiprocessing.get_logger()
    (process_id,) = multiprocessing.current_process()._identity
    logger.info(f"process_id: {process_id}")
    # Assume process_id to be a unique integer from 1 to the number of worker threads
    nixpkgs = nixpkgs_worktrees[process_id - 1]
    logger.info(f"Working on package {package_metadata["attribute_name"]} in Nixpkgs {nixpkgs}")

    utils.reset_nixpkgs_git(nixpkgs)

    # Check that it still compiles
    (build_result, compile_time_ns) = utils.nix_build(nixpkgs, package_metadata)

    if build_result.returncode != 0:
        raise Exception("The package does not currently compile!")

    nix_code = utils.read_nix_code(nixpkgs, package_metadata)

    if random.random() >= 0.9:
        code_breaking_algorithm = 1
        broken_nix_code = break_code_v1.execute(nix_code)
    else:
        code_breaking_algorithm = 2
        broken_nix_code = break_code_v2.execute(nix_code)

    utils.write_nix_code(nixpkgs, package_metadata, broken_nix_code)

    # Try to compile the package and get the error message
    (build_result, compile_time_ns) = utils.nix_build(nixpkgs, package_metadata)

    if build_result.returncode == 0:
        logger.info("We did not manage to break the code! Ignoring. 🤷")
        return (package_metadata, nixpkgs_rev_bin, code_breaking_algorithm, nix_code, broken_nix_code, build_result.stderr, None, compile_time_ns)

    logger.info("The nix-build command failed, let's see what the error was. 🗒")
    error_message = common_utils.parse_error_from_nix_output(build_result.stderr)
    logger.info("One item done 🎉")
    return (package_metadata, nixpkgs_rev_bin, code_breaking_algorithm, nix_code, broken_nix_code, build_result.stderr, error_message, compile_time_ns)


def collect_one_sample_catch_exceptions(package_metadata):
    try:
        return collect_one_sample(package_metadata)
    except Exception:
        logger = multiprocessing.get_logger()
        logger.info(f"Got an exception: {traceback.format_exc()}")
    return None


"""
To try out db.save_to_dataset():
dummy_package_metadata = {
    "pname": "",
    "attribute_name": "",
    "system": "",
    "position": {
        "file": "",
        "line": 0,
    },
}
dummy_results = (dummy_package_metadata, b"", "", "", "", None, 0)
db.save_to_dataset(dummy_results)
assert False"""

# TODO: let this if statement also cover all the other code in this file
if __name__ == '__main__':
    multiprocessing.log_to_stderr(logging.INFO)

    with Pool(len(nixpkgs_worktrees)) as pool:
        for results in pool.imap_unordered(collect_one_sample_catch_exceptions, packages_metadata):
            if results:
                db.save_to_dataset(results)
