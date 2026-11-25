# nightjob — unattended GPU jobs on a ROCm card: VRAM preflight, a transient
# systemd unit with a wall-clock budget, a ROCm sampler and a morning report.
#
# The CLI is stdlib-only Python, so the package is a wrapper: the interpreter
# and the tools it shells out to ride in its PATH, and the caller's PATH stays
# behind them — `hyprctl` (window titles in preflight) and `llmctl` (the
# graceful llama-swap unload) come from the session, not from here.
{
  lib,
  writeShellScriptBin,
  python3,
  fzf,
  rocmPackages,
  pciutils,
  systemd,
  libnotify,
  coreutils,
}:
let
  wrapper = writeShellScriptBin "nightjob" ''
    export PATH="${
      lib.makeBinPath [
        python3
        fzf # interactive multi-select of the apps to close
        rocmPackages.rocm-smi # GPU sampler (unused when fdinfo suffices)
        pciutils # lspci: the card's marketing name
        systemd # systemd-run / systemctl / journalctl
        libnotify # notify-send when the job ends
        coreutils # tail, sleep
      ]
    }:$PATH"
    exec ${python3}/bin/python3 ${./nightjob.py} "$@"
  '';
in
wrapper.overrideAttrs (_: {
  meta = {
    description = "Unattended GPU jobs: VRAM preflight, systemd runner, ROCm venv, morning report";
    homepage = "https://github.com/neg-serg/nightjob";
    platforms = lib.platforms.linux;
    maintainers = [ ];
    mainProgram = "nightjob";
  };
})
