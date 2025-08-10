# An AI agent to package a software project for Nixpkgs using Nix

## Key Functionality

* Use [nix-init](https://github.com/nix-community/nix-init) to generate a (probably not yet working) Nix package
* Try to build the package and record the error message
* Use an LLM to analyze the error message and try to fix it
* Repeat the previous two steps until it succeeds
* Store all steps in Git for easy review and experimentation

## Get Started

1. Run on Linux, as this was not tested on other operating systems
2. Clone this repo
3. [Install Nix](https://zero-to-nix.com/start/install)
4. Enter development environment: `nix develop`
5. Setup LLM
  * If using a local model (Ollama)
    1. Install Ollama
    2. Choose a model
    3. Download the model
    4. Change the code?
  * If using OpenAI
    1. Copy `.OpenAI-API-Key-example.sh` to `.OpenAI-API-Key.sh`
    2. Edit `.OpenAI-API-Key.sh` to add an actual API key
    3. Change the code?
6. Run `jupyter-lab` and open `AI-Nix-Packager.ipynb`
7. Pick a project or program, which is not yet packaged in Nixpkgs
8. Edit the code and add the program name
9. Run all the cells
10. When prompted to do so, run nix-init and answer its questions
11. Run all remaining cells
12. Cross your fingers
13. Be patient
14. With some luck, you may now have a working Nix derivation to build your package
15. You still need to manually review the package as the LLM may have generated bad code
