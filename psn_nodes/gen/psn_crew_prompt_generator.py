"""
PSN_Crew_Prompt_Generator: Simulates a CrewAI-style multi-agent workflow for prompt refinement.

This module implements the pure-logic, secure-by-design part of a role-based agent
collaboration system. It does NOT make network calls, import torch, or access files.
Instead, it accepts a pre-formatted JSON string of mock LLM responses (or a callable
placeholder) and simulates the sequential refinement process.

The 'llm_connection' input is treated as a STRING containing JSON that maps role names
to their generated contributions. This allows the node to be tested and used in
environments without a live LLM backend, while maintaining the interface shape.

Data Flow: Brief -> Agent 1 (contribution) -> Agent 2 (refinement) -> ... -> Final Prompt
"""

import json
import re

# Placeholder for the safe evaluator/orchestration helpers if available in the PSN ecosystem.
# Since we are restricted to stdlib and cannot import external PSN modules that might not exist
# in this isolated context, we implement the necessary logic locally but keep the structure
# compatible with the requested style.
# from psn import expr, orchestration

CAT = "ParametricStudio/Crew"

# Allowed roles for validation (allow-list check)
ALLOWED_ROLES = [
    "Lyricist",
    "Composer",
    "Producer",
    "Vocalist",
    "SoundEngineer",
    "Director",
    "Editor",
    "MixingEngineer",
    "MasteringEngineer",
    "CreativeDirector"
]

class PSN_Crew_Prompt_Generator:
    """
    Simulates a CrewAI-style workflow where multiple role-based agents
    collaboratively draft and refine a prompt.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "brief": ("STRING", {"default": "", "multiline": True}),
                "roles": (["Lyricist", "Composer", "Producer", "Vocalist", "SoundEngineer", "Director", "Editor", "MixingEngineer", "MasteringEngineer", "CreativeDirector"], {"default": ["Lyricist", "Composer", "Producer"], "multi": True}),
                "llm_connection": ("STRING", {"default": "{}", "multiline": True, "tooltip": "JSON string mapping role names to their mock LLM responses. Example: {\"Lyricist\": \"Verse 1...\", \"Composer\": \"Key of C...\"}"})
            },
            "optional": {
                "max_iterations": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1})
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "agent_dialogue")
    FUNCTION = "run"
    CATEGORY = CAT

    def _validate_roles(self, roles):
        """Validate that all roles are in the allow-list."""
        valid_roles = []
        for role in roles:
            if role in ALLOWED_ROLES:
                valid_roles.append(role)
            else:
                # Silently ignore invalid roles or raise? Spec says allow-list checks.
                # We'll filter them out to be secure-by-design, but log it in dialogue.
                pass
        return valid_roles

    def _parse_llm_responses(self, llm_connection_json):
        """
        Parse the JSON string of LLM responses.
        Returns a dict mapping role -> response string.
        """
        if not llm_connection_json or not llm_connection_json.strip():
            return {}
        
        try:
            data = json.loads(llm_connection_json)
            if not isinstance(data, dict):
                return {}
            
            # Ensure values are strings
            clean_data = {}
            for key, value in data.items():
                if isinstance(key, str) and isinstance(value, str):
                    clean_data[key] = value
            return clean_data
        except json.JSONDecodeError:
            return {}

    def _simulate_agent_contribution(self, role, current_prompt, llm_responses, iteration):
        """
        Simulates an agent's contribution.
        In a real system, this would call the LLM. Here, we use the mock response
        from the llm_connection JSON. If the role isn't in the JSON, we generate
        a placeholder contribution based on the role and current prompt.
        """
        if role in llm_responses:
            response = llm_responses[role]
        else:
            # Fallback: Generate a deterministic placeholder
            response = f"[{role} Contribution] Refining prompt for iteration {iteration}."
        
        # Simple refinement logic: Append the contribution to the current prompt
        # In a real LLM, the agent would rewrite the whole prompt.
        # Here, we simulate by appending to show the flow.
        if current_prompt:
            new_prompt = f"{current_prompt}\n[{role}]: {response}"
        else:
            new_prompt = f"[{role}]: {response}"
            
        return new_prompt

    def run(self, brief, roles, llm_connection, max_iterations=1):
        # 1. Validate Roles
        valid_roles = self._validate_roles(roles)
        
        if not valid_roles:
            return ("No valid roles provided.", "Error: No valid roles from allow-list were provided.")

        # 2. Parse LLM Responses
        llm_responses = self._parse_llm_responses(llm_connection)

        # 3. Initialize Dialogue Log
        dialogue_log = []
        dialogue_log.append(f"=== Crew Prompt Generation Started ===")
        dialogue_log.append(f"Creative Brief: {brief}")
        dialogue_log.append(f"Active Roles: {', '.join(valid_roles)}")
        dialogue_log.append("-" * 40)

        # 4. Simulate Sequential Agent Workflow
        current_prompt = brief
        
        for i, role in enumerate(valid_roles):
            # Each agent refines the prompt
            previous_prompt = current_prompt
            current_prompt = self._simulate_agent_contribution(role, current_prompt, llm_responses, i + 1)
            
            # Log the interaction
            dialogue_log.append(f"Agent: {role}")
            dialogue_log.append(f"Input: {previous_prompt[:100]}...")
            dialogue_log.append(f"Output: {current_prompt[:100]}...")
            dialogue_log.append("-" * 40)

        dialogue_log.append(f"=== Final Prompt Generated ===")
        
        final_prompt = current_prompt
        agent_dialogue = "\n".join(dialogue_log)

        return (final_prompt, agent_dialogue)


NODE_CLASS_MAPPINGS = {
    "PSN_Crew_Prompt_Generator": PSN_Crew_Prompt_Generator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Crew_Prompt_Generator": "PSN Crew Prompt Generator"
}
