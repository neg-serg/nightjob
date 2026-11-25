# nightjob

Unattended GPU jobs on a ROCm card: a VRAM preflight, a transient systemd unit
with a wall-clock budget, a ROCm sampler and a morning report.

```
nightjob preflight --need-gb 12   # who holds VRAM; close apps via fzf
nightjob run --budget 8h -- python train.py
nightjob status | logs -f | report
nightjob env init                 # ROCm venv at /zero/ai/venvs/train
```

- **preflight** reads `drm-total-vram` from the kernel's fdinfo, so it needs no
  root and no `rocm-smi` KFD dependency. It groups PIDs by application (window
  titles from `hyprctl` when available) and can close what you pick until the
  budget fits.
- **run** launches the command under a transient user unit with `KillMode=mixed`
  (so `stop` becomes SIGINT and the trainer can checkpoint), retries from the
  checkpoint, samples `rocm-smi` into a CSV next to the log, and writes
  `final.json` plus `report.md`.
- **env** creates or checks the training venv from the official PyTorch ROCm
  wheels.

State lives in `~/.local/state/nightjob/<unit>/<timestamp>/` and nowhere else.
The CLI is stdlib-only Python; `systemd-run`, `fzf` and `rocm-smi` come from
`PATH`, and `hyprctl`/`llmctl` are used when the session has them.

## Build and test

```bash
nix build .#default   # the wrapper with its tool PATH
nix flake check       # builds the package and runs test_nightjob.py
python3 -m unittest discover -v   # the suite alone, no Nix needed
```

The suite has no device dependency: it covers the duration/size grammars, the
state-directory contract, the CLI surface, the exit-code wording and the shell
quoting.

## How the host consumes it

```nix
nightjob = final.callPackage (inputs.nightjob + "/package.nix") { };
```

The host keeps the ROCm feature flag and installs `pkgs.neg.nightjob`; the
training venv is a pip environment, not a Nix package.
