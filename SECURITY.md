# Security

## Reporting a problem

Please do not open a public issue. Use GitHub's private vulnerability reporting on this repository (Security tab, "Report a vulnerability"). This is a one-person open-source project, so there is no response-time guarantee, but reports will be read.

If a token or key is ever found in this repository or its history, say so in the report. Do not paste its value.

## What the studio is

A local tool for one person on their own machine. Know these before you change how it runs:

- **No login.** The API has no authentication. It binds to `127.0.0.1` by default. If you set `STUDIO_HOST=0.0.0.0` or put it behind a tunnel, anyone who reaches the port can queue jobs on your GPU, upload files, start model downloads, edit schedules and read your outputs. Use a private network such as a VPN or LAN you trust, and put your own authentication in front of anything wider. The same applies to ComfyUI.
- **The Open edition makes few outside calls:** Civitai and Hugging Face catalogue lookups, downloads after you confirm, and the optional GitHub link and notification bridges you set up.
- **Licences are not a technical control.** The studio shows each model's licence; following it is up to you. See [MODELS.md](MODELS.md).

## Guards in the code

These are defence in depth. They have tests, including adversarial inputs, but they have not had an independent security audit.

| Area | What it does | Limits |
|---|---|---|
| `PSN_Expression` | Evaluates a whitelisted expression tree; never calls `eval` or `exec` | Bounded size and results |
| `PSN_SandboxScript` | Runs a script in a separate, resource-limited process with an import allow-list, no network and no files | Not an operating-system sandbox. Do not run hostile code on a machine you care about |
| Subagents | Acting tools are restricted to a private workspace, and a command guard blocks destructive commands and credential paths | A guard list can be incomplete. There is no tool that posts, spends, deletes or installs; those requests stop and ask |
| Model downloads | The installer and browser check SHA-256 and ask first. Civitai fetches only `.safetensors` | Hugging Face and Civitai can host malicious models; prefer safetensors and known authors |
| File routes | Output and 3D routes resolve paths and refuse anything outside the output folder | |
| Imported workflows | Scanned for adult-content terms. Remote ComfyUI addresses must be loopback or private unless `STUDIO_ALLOW_REMOTE=1` | Importing a workflow can still pull in custom nodes, which run with full rights. Read a node pack before you install it |

## Secrets

- `HF_TOKEN`, `CIVITAI_TOKEN` and `GITHUB_TOKEN` are read from the environment and are not written to disk. The installer sends `HF_TOKEN` only to huggingface.co, and drops it on a redirect to a CDN.
- Bridge settings (Telegram, Discord, Slack, ntfy) live in your own config file, which should be readable only by you.
- Never commit `.env` files or tokens. CI runs `.github/scripts/repo_checks.py`, which reports matches by file and line only.

## Supported versions

Only the latest commit on the default branch.
