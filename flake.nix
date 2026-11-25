{
  description = "nightjob — unattended GPU jobs on a ROCm card (VRAM preflight, systemd runner, morning report)";

  # The host flake (/etc/nixos) calls `package.nix` through `final.callPackage`
  # against its own package set, so this pin decides only what `nix build` and
  # `nix flake check` do here.
  # Pinned to the rev the host runs, so `nix build` here reuses the same
  # package set (the host itself calls `package.nix` through callPackage).
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/2786a2a72088ecf32aea5b3ec52099e6a7cff78f";

  outputs =
    { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAllSystems (pkgs: {
        default = pkgs.callPackage ./package.nix { };
      });

      checks = forAllSystems (pkgs: {
        build = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
        # The suite is stdlib-only, so it runs against the checkout without a
        # device: copy it out of the store first, because Python wants to
        # write bytecode next to the sources.
        unit = pkgs.runCommand "nightjob-unit-tests" { nativeBuildInputs = [ pkgs.python3 ]; } ''
          cp -r ${self} src
          cd src
          python3 -m unittest discover -v
          touch $out
        '';
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python3
            pkgs.nixfmt
          ];
        };
      });

      formatter = forAllSystems (pkgs: pkgs.nixfmt);
    };
}
