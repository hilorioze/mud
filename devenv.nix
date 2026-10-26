{pkgs, ...}: {
  languages = {
    # keep-sorted start block=yes newline_separated=yes
    nix = {
      enable = true;

      lsp.package = pkgs.nil;
    };

    python = {
      enable = true;

      uv = {
        enable = true;

        sync.enable = true;
      };

      # `uv.sync` creates the venv but doesn't add it to `PATH`
      venv.enable = true;
    };
    # keep-sorted end
  };

  enterTest = "pytest";

  treefmt = {
    enable = true;

    config.programs = {
      # keep-sorted start block=yes newline_separated=yes
      alejandra = {
        enable = true;

        priority = 100;
      };

      deadnix.enable = true;

      keep-sorted.enable = true;

      ruff-check.enable = true;

      ruff-format.enable = true;

      statix.enable = true;
      # keep-sorted end
    };
  };

  git-hooks.hooks = {
    # keep-sorted start block=yes newline_separated=yes
    actionlint = {
      enable = true;

      args = ["-ignore=SC2086"]; # unquoted variables; the referenced ones are safe
    };

    check-merge-conflicts = {
      enable = true;

      fail_fast = true; # abort immediately so treefmt never runs on conflicted files
    };

    # use `.editorconfig` as the single source of truth for generic file normalization
    eclint = {
      enable = true;

      types = ["text"];

      # `eclint` only processes the first positional path, so let it discover tracked files itself
      pass_filenames = false;

      settings.fix = true;
    };

    pyright.enable = true;

    treefmt = {
      enable = true;

      after = ["check-merge-conflicts"];
    };
    # keep-sorted end
  };

  devcontainer = {
    enable = true;

    settings = {
      # cache `/nix` between rebuilds
      mounts = ["source=devcontainer-nix,target=/nix,type=volume"];

      customizations.vscode.extensions = [
        # keep-sorted start
        "EditorConfig.EditorConfig"
        "charliermarsh.ruff"
        "jnoortheen.nix-ide"
        "mkhl.direnv"
        "ms-python.python"
        # keep-sorted end
      ];
    };
  };

  # ensure generated files (like `.devcontainer/devcontainer.json`) exist before `treefmt` runs to prevent race conditions
  tasks."devenv:treefmt:run".after = ["devenv:files"];
}
