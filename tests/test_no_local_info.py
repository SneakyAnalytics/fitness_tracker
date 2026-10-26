"""The repository is public: nothing in it may identify the machines, network or accounts behind the app.

Machine-specific values (server address, usernames, folders, keys) belong in the git-ignored
deploy.local.env, AGENTS.local.md and .env. Use placeholders such as <user>, <beelink-ip> or
%USERPROFILE% in anything committed. The patterns here are deliberately generic, so this file
holds no private values itself.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = (".jpg", ".jpeg", ".png", ".webp", ".ico", ".gif", ".pyc", ".db", ".gz", ".zip", ".woff", ".woff2",
          ".pdf", ".fit", ".app", ".tar", ".pickle")
SKIP = ("frontend/package-lock.json", "tests/test_no_local_info.py")

# A path segment counts as a placeholder if it starts with one of these.
PLACEHOLDER = r"(?![<%$\{\[]|your|Your|YOUR|username|USERNAME|user\b|<)"

CHECKS = {
    "a private-network or Tailscale address": re.compile(
        r"(?<![\d.])(?:100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|192\.168\.\d{1,3}|10\.\d{1,3}\.\d{1,3}|"
        r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3})\.\d{1,3}(?![\d.])"),
    "a Windows user folder": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+" + PLACEHOLDER + r"[A-Za-z0-9_.-]+(?![A-Za-z0-9_.-]*[>])"),
    "a Mac or Linux home folder": re.compile(r"(?<![\w.])/(?:Users|home)/" + PLACEHOLDER + r"[A-Za-z0-9_.-]+"),
    "an SSH public key": re.compile(r"ssh-(?:ed25519|rsa) AAAA"),
    "a personal email address": re.compile(
        r"[\w.+-]+@(?:gmail|googlemail|outlook|hotmail|icloud|yahoo|proton|protonmail)\.com", re.I),
    "an API token": re.compile(r"(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{30,}|"
                               r"AIza[0-9A-Za-z_-]{30,}|xox[bp]-[A-Za-z0-9-]{20,})"),
}
# One home-folder example that is generic by construction.
ALLOWED = ("/Users/<", "/home/<", "/home/app", "/home/runner", "/home/node", "/home/user")


def tracked_text_files():
    names = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    for name in names:
        if name.endswith(BINARY) or name in SKIP:
            continue
        try:
            yield name, (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue


def test_nothing_machine_specific_is_committed():
    problems = []
    for name, text in tracked_text_files():
        for label, pattern in CHECKS.items():
            for match in pattern.finditer(text):
                found = match.group(0)
                if any(found.startswith(ok) for ok in ALLOWED):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{name}:{line}: {label} ({found[:40]})")
    assert not problems, "machine-specific details in tracked files:\n  " + "\n  ".join(problems[:40])
