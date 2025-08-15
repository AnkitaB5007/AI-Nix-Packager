import os
import json
import time
import logging
import sqlite3
import subprocess
from pathlib import Path

class DB:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS dataset_raw(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pname TEXT NOT NULL,
                attribute_name TEXT NOT NULL,
                system TEXT NOT NULL,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                nixpkgs_revision BLOB NOT NULL,
                code_breaking_algorithm INTEGER,
                nix_code_working TEXT NOT NULL,
                nix_code_broken TEXT NOT NULL,
                full_nix_output TEXT NOT NULL,
                error_message TEXT,
                compile_time_ns INTEGER NOT NULL
            )
        """)
        """self.cur.execute(""
            INSERT INTO dataset_raw_new (
                id,
                pname,
                attribute_name,
                system,
                file,
                line,
                nixpkgs_revision,
                nix_code_working,
                nix_code_broken,
                full_nix_output,
                error_message,
                compile_time_ns
            ) SELECT
                id,
                pname,
                attribute_name,
                system,
                file,
                line,
                nixpkgs_revision,
                nix_code_working,
                nix_code_broken,
                full_nix_output,
                error_message,
                compile_time_ns
            FROM dataset_raw;
        "")"""
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS cache(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nixpkgs_revision BLOB NOT NULL,
                nix_env_output TEXT NOT NULL
            )
        """)
        self.cur.execute("""
            DROP VIEW IF EXISTS dataset;
        """)
        self.cur.execute("""
            CREATE VIEW IF NOT EXISTS dataset(
                id,
                pname,
                attribute_name,
                system,
                file,
                nixpkgs_revision,
                code_breaking_algorithm,
                nix_code_working,
                nix_code_broken,
                error_message,
                compile_time_s
            )
            AS
            SELECT
                id,
                pname,
                attribute_name,
                system,
                file,
                LOWER(HEX(nixpkgs_revision)),
                code_breaking_algorithm,
                nix_code_working,
                nix_code_broken,
                error_message,
                compile_time_ns / 1000 / 1000 / 1000
            FROM dataset_raw;
        """)
        self.cur.execute("""
            DROP VIEW IF EXISTS dataset_lite;
        """)
        self.cur.execute("""
            CREATE VIEW IF NOT EXISTS dataset_lite(
                error_message,
                id,
                pname,
                attribute_name,
                system,
                file,
                nixpkgs_revision,
                code_breaking_algorithm,
                compile_time_s
            )
            AS
            SELECT
                error_message,
                id,
                pname,
                attribute_name,
                system,
                file,
                nixpkgs_revision,
                code_breaking_algorithm,
                compile_time_s
            FROM dataset;
        """)
        self.con.commit()


    def write_cache(self, nixpkgs_rev_bin, nix_env_output):
        self.cur.executemany("""
            INSERT INTO cache(
                nixpkgs_revision,
                nix_env_output
            )
            VALUES(?, ?)""", [(nixpkgs_rev_bin, nix_env_output)])
        self.con.commit()


    def read_cache(self, nixpkgs_rev_bin):
        self.cur.execute("SELECT nix_env_output FROM cache WHERE nixpkgs_revision = ?", (nixpkgs_rev_bin,))
        return self.cur.fetchone()


    def save_to_dataset(self, results):
        (package_metadata, nixpkgs_rev_bin, code_breaking_algorithm, nix_code, broken_nix_code, stderr, error_message, compile_time_ns) = results
        data = [(
            package_metadata["pname"],
            package_metadata["attribute_name"],
            package_metadata["system"],
            str(package_metadata["position"]["file"]),
            package_metadata["position"]["line"],
            nixpkgs_rev_bin,
            code_breaking_algorithm,
            nix_code,
            broken_nix_code,
            stderr,
            error_message,
            compile_time_ns,
        )]
        self.cur.executemany("""
        INSERT INTO dataset_raw(
            pname,
            attribute_name,
            system,
            file,
            line,
            nixpkgs_revision,
            code_breaking_algorithm,
            nix_code_working,
            nix_code_broken,
            full_nix_output,
            error_message,
            compile_time_ns
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
        self.con.commit()


    def read_from_dataset(self, limit=None):
        query_first_part = """
            SELECT
                id,
                pname,
                attribute_name,
                system,
                file,
                nixpkgs_revision,
                code_breaking_algorithm,
                nix_code_working,
                nix_code_broken,
                error_message,
                compile_time_s
            FROM dataset WHERE error_message is not NULL ORDER BY RANDOM()
        """
        if limit is None:
            self.cur.execute(f"{query_first_part};")
        else:
            self.cur.execute(f"{query_first_part} LIMIT ?;", (limit,))
        # TODO: stream results somehow
        return self.cur.fetchall()



# Make sure the Nixpkgs repository is in a clean state
def reset_nixpkgs_git(nixpkgs):
    _ = subprocess.run(("git", "add", "--all"), cwd=nixpkgs, check=True)
    _ = subprocess.run(("git", "reset", "--hard"), cwd=nixpkgs, check=True, stdout=subprocess.DEVNULL)


def read_nixpkgs_rev(nixpkgs):
    return subprocess.run(("git", "rev-parse", "--verify", "HEAD^{commit}"), cwd=nixpkgs, check=True, capture_output=True, encoding='utf-8').stdout.strip()


def nixpkgs_rev_str_to_bin(nixpkgs_rev_str):
    return int(nixpkgs_rev_str, 16).to_bytes(20, byteorder='big')


def get_all_pkgs_from_nixpkgs(nixpkgs):
    query_result = subprocess.run(
        (
            "nix-env",
            "--query",
            "--available",
            "--attr-path",
            "--out-path",
            "--meta",
            "--json",
            "--arg", "config", "{ allowAliases = false; }", # override default nixpkgs config discovery
            "--arg", "overlays", "[ ]",
            "--file", nixpkgs,
        ),
        check=True,
        stdout=subprocess.PIPE,
        encoding='utf-8',
    )
    return query_result.stdout


def get_all_pkgs_cached(db, nixpkgs_rev_bin, nixpkgs):
    logger = logging.getLogger(__name__)
    row = db.read_cache(nixpkgs_rev_bin)
    if row is None:
        logger.info("Listing all packages from Nixpkgs, this will take some time and a lot of RAM...")
        all_pkgs = get_all_pkgs_from_nixpkgs(nixpkgs)
        logger.info("Done.")
        db.write_cache(nixpkgs_rev_bin, all_pkgs)
    else:
        all_pkgs = row[0]

    all_pkgs = json.loads(all_pkgs)

    def filter_function(arg):
        (attribute_name, package) = arg
        if "meta" not in package:
            return False
        if "position" not in package["meta"]:
            return False
        return True
    all_pkgs_filtered = dict(filter(filter_function, all_pkgs.items()))

    logger.info(f"There are a total of {len(all_pkgs)} packages in Nixpkgs, with {len(all_pkgs_filtered)} of them having all the information we require")
    return all_pkgs_filtered


def extract_metadata(nixpkgs, package_attr, package):
    logger = logging.getLogger(__name__)
    if "meta" not in package:
        logger.info(f"No metadata for package {package_attr}! Skipping this package.")
        return None
    if "position" not in package["meta"]:
        logger.info(f"No position in metadata for package {package_attr}! Skipping this package.")
        return None
    position_raw = package["meta"]["position"]
    position_pieces = position_raw.split(":")
    assert len(position_pieces) == 2
    file = Path(position_pieces[0])
    assert file.is_file()
    nixpkgs_abs = os.path.abspath(nixpkgs)
    rel_file = file.relative_to(nixpkgs_abs) # relative_to() throws an exception if file is not a subdirectory of nixpkgs
    return {
        "attribute_name": package_attr,
        "pname": package["pname"],
        "system": package["system"],
        "position": {
            "file": rel_file,
            "line": int(position_pieces[1]),
        },
    }


def nix_build(nixpkgs, metadata):
    start_time = time.time()
    build_result = subprocess.run(
        (
            "nix-build",
            "--no-out-link",
            "--log-format", "internal-json",
            "-A", metadata["attribute_name"],
        ),
        capture_output=True,
        encoding='utf-8',
        cwd=nixpkgs,
        check=False,
        env={
            "PATH": os.getenv("PATH"),
            "NO_COLOR": "", # TODO: debug Nix why this has no effect when --log-format is internal-json
            "NIXPKGS_ALLOW_UNFREE": "1",
        },
    )
    end_time = time.time()
    compile_time_float = end_time - start_time
    compile_time_ns = int(compile_time_float * 1000 * 1000 * 1000)
    return (build_result, compile_time_ns)


def read_nix_code(nixpkgs, package_metadata):
    with open(nixpkgs / package_metadata["position"]["file"], "r", encoding='utf-8') as f:
        return f.read()


def write_nix_code(nixpkgs, package_metadata, broken_nix_code):
    with open(nixpkgs / package_metadata["position"]["file"], "w", encoding='utf-8') as f:
        f.write(broken_nix_code)
