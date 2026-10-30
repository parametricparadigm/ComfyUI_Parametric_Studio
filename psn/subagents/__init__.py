"""Subagents: role-based, budgeted, verified model workers. See roles.py (what each role is) and runner.py (how one runs)."""
from psn.subagents.roles import ROLES
from psn.subagents.runner import run_subagent, resume_subagent, Result
from psn.subagents.fanout import fan_out, join
__all__ = ["ROLES", "run_subagent", "resume_subagent", "Result", "fan_out", "join"]
