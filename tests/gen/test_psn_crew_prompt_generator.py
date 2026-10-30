import pytest
import json
from psn_nodes.gen.psn_crew_prompt_generator import PSN_Crew_Prompt_Generator, ALLOWED_ROLES

class TestPSNCrewPromptGenerator:
    def setup_method(self):
        self.node = PSN_Crew_Prompt_Generator()

    def test_basic_workflow_with_mock_responses(self):
        """Test that the final prompt contains contributions from all roles."""
        brief = "Create a rock song"
        roles = ["Lyricist", "Composer"]
        llm_json = json.dumps({
            "Lyricist": "Verse 1: I am the rock",
            "Composer": "Key of G, 120 BPM"
        })
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "Create a rock song" in final_prompt
        assert "Verse 1: I am the rock" in final_prompt
        assert "Key of G, 120 BPM" in final_prompt
        assert "Lyricist" in dialogue
        assert "Composer" in dialogue

    def test_invalid_roles_are_filtered(self):
        """Test that roles not in the allow-list are ignored."""
        brief = "Test brief"
        roles = ["Lyricist", "Hacker", "Composer"]
        llm_json = json.dumps({
            "Lyricist": "Lyrics here",
            "Hacker": "Should not appear",
            "Composer": "Music here"
        })
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "Lyrics here" in final_prompt
        assert "Music here" in final_prompt
        assert "Should not appear" not in final_prompt
        assert "Hacker" not in dialogue

    def test_empty_llm_connection_uses_fallback(self):
        """Test that if LLM JSON is empty, fallback placeholders are used."""
        brief = "Test brief"
        roles = ["Lyricist"]
        llm_json = "{}"
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "Lyricist" in final_prompt
        assert "[Lyricist Contribution]" in final_prompt

    def test_invalid_json_llm_connection(self):
        """Test that invalid JSON in llm_connection is handled gracefully."""
        brief = "Test brief"
        roles = ["Lyricist"]
        llm_json = "not a json"
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        # Should still produce output using fallback
        assert "Lyricist" in final_prompt
        assert "[Lyricist Contribution]" in final_prompt

    def test_no_valid_roles(self):
        """Test behavior when no valid roles are provided."""
        brief = "Test brief"
        roles = ["InvalidRole1", "InvalidRole2"]
        llm_json = "{}"
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "No valid roles" in final_prompt
        assert "Error" in dialogue

    def test_single_role_workflow(self):
        """Test workflow with a single role."""
        brief = "Create a jazz piece"
        roles = ["Composer"]
        llm_json = json.dumps({
            "Composer": "Swing time, 100 BPM"
        })
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "Create a jazz piece" in final_prompt
        assert "Swing time, 100 BPM" in final_prompt
        assert "Composer" in dialogue

    def test_multiple_iterations_same_role(self):
        """Test that the same role can appear multiple times (though typically unique)."""
        brief = "Test"
        roles = ["Lyricist", "Lyricist"]
        llm_json = json.dumps({
            "Lyricist": "First verse"
        })
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        # The same response is used for both iterations
        assert final_prompt.count("First verse") == 2

    def test_dialogue_log_structure(self):
        """Test that the dialogue log has the expected structure."""
        brief = "Test brief"
        roles = ["Lyricist", "Composer"]
        llm_json = json.dumps({
            "Lyricist": "Lyrics",
            "Composer": "Music"
        })
        
        final_prompt, dialogue = self.node.run(brief, roles, llm_json)
        
        assert "=== Crew Prompt Generation Started ===" in dialogue
        assert "=== Final Prompt Generated ===" in dialogue
        assert "Creative Brief: Test brief" in dialogue
        assert "Active Roles: Lyricist, Composer" in dialogue
