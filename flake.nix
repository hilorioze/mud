{
  inputs = {
    # keep-sorted start block=yes newline_separated=yes
    flake-parts.url = "github:hercules-ci/flake-parts";

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";

      inputs = {
        nixpkgs.follows = "nixpkgs";

        # keep-sorted start
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        # keep-sorted end
      };
    };

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";

      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";

      inputs = {
        nixpkgs.follows = "nixpkgs";

        pyproject-nix.follows = "pyproject-nix";
      };
    };
    # keep-sorted end

    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  };

  outputs = inputs @ {
    # keep-sorted start
    flake-parts,
    nixpkgs,
    pyproject-build-systems,
    pyproject-nix,
    uv2nix,
    # keep-sorted end
    ...
  }: let
    inherit (nixpkgs) lib;

    systems = [
      # keep-sorted start
      "aarch64-linux"
      "x86_64-linux"
      # keep-sorted end
    ];

    # versions come from `uv.lock`: nixpkgs has no adaptix and older telnetlib3 and wcwidth
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};
  in
    flake-parts.lib.mkFlake {inherit inputs;} {
      inherit systems;

      perSystem = {system, ...}: let
        pkgs = import nixpkgs {inherit system;};

        pythonSet = (pkgs.callPackage pyproject-nix.build.packages {python = pkgs.python314;}).overrideScope (lib.composeManyExtensions [
          pyproject-build-systems.overlays.wheel
          (workspace.mkPyprojectOverlay {sourcePreference = "wheel";})
        ]);

        # only the `mud` command, without the interpreter and the rest of the venv
        application = (pkgs.callPackages pyproject-nix.build.util {}).mkApplication {
          venv = pythonSet.mkVirtualEnv "mud-env" workspace.deps.default;

          package = pythonSet.mud;
        };

        package = application.overrideAttrs {
          meta = {
            description = "Small multiplayer text game played over telnet";
            homepage = "https://github.com/hilorioze/mud";

            license = lib.licenses.mit;

            mainProgram = "mud";

            platforms = systems;
          };
        };
      in {
        packages = {
          # keep-sorted start
          default = package;
          mud = package;
          # keep-sorted end
        };
      };

      flake.overlays.default = _final: prev: {inherit (inputs.self.packages.${prev.stdenv.hostPlatform.system}) mud;};
    };
}
