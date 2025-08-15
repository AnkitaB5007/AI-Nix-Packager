{
  description = "AI Nix Packager";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }: let
    lib = nixpkgs.lib;
    forAllSystems = function: lib.genAttrs [
      "aarch64-linux"
      "x86_64-linux"
    ] function;
  in {
    devShells = forAllSystems (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      pythonEnv = pkgs.python3.withPackages (ps: with ps; [
        jupyterlab
        pydantic
        python-dotenv
      ]);
    in {
      default = pkgs.mkShellNoCC {
        packages = [
          pythonEnv
          pkgs.nix-init
        ];

        shellHook = ''
          export PYTHONPATH="${lib.getExe pythonEnv}"
        '';
      };
    });
  };
}
