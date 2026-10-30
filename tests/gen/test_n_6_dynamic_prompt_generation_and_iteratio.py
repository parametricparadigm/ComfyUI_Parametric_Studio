"""Tests for PSN_Prompt_Generator and PSN_Prompt_Iterator nodes."""

import pytest

from psn_nodes.gen.n_6_dynamic_prompt_generation_and_iteratio import (
    PSN_Prompt_Generator,
    PSN_Prompt_Iterator,
)


class TestPSN_Prompt_Generator:
    def test_basic_generation_count(self):
        """Generate prompts and verify the count matches num_variations."""
        node = PSN_Prompt_Generator()
        template = "a {animal} in the {place}"
        variables = "animal:cat,dog;place:park,forest"
        result = node.run(template, variables, 5, seed=42)
        prompts = result[0]
        assert len(prompts) == 5

    def test_basic_generation_content(self):
        """Verify that generated prompts contain valid substitutions."""
        node = PSN_Prompt_Generator()
        template = "a {animal} in the {place}"
        variables = "animal:cat,dog;place:park,forest"
        result = node.run(template, variables, 4, seed=123)
        prompts = result[0]
        valid_animals = {"cat", "dog"}
        valid_places = {"park", "forest"}
        for prompt in prompts:
            assert "{" not in prompt, f"Unsubstituted placeholder in: {prompt}"
            assert "}" not in prompt, f"Unsubstituted placeholder in: {prompt}"
            # Check that the prompt matches the expected pattern
            parts = prompt.split(" in the ")
            assert len(parts) == 2
            animal = parts[0].replace("a ", "")
            place = parts[1]
            assert animal in valid_animals, f"Invalid animal: {animal}"
            assert place in valid_places, f"Invalid place: {place}"

    def test_deterministic_with_seed(self):
        """Same seed should produce the same prompts."""
        node = PSN_Prompt_Generator()
        template = "a {color} {object}"
        variables = "color:red,blue,green;object:car,tree"
        result1 = node.run(template, variables, 3, seed=999)
        result2 = node.run(template, variables, 3, seed=999)
        assert result1[0] == result2[0]

    def test_different_seeds_produce_different_results(self):
        """Different seeds should (with high probability) produce different prompts."""
        node = PSN_Prompt_Generator()
        template = "a {color} {object}"
        variables = "color:red,blue,green,yellow,purple;object:car,tree,house,boat"
        result1 = node.run(template, variables, 10, seed=1)
        result2 = node.run(template, variables, 10, seed=2)
        assert result1[0] != result2[0]

    def test_missing_variable_raises_error(self):
        """Template with a placeholder not in variables should raise ValueError."""
        node = PSN_Prompt_Generator()
        template = "a {animal} and a {bird}"
        variables = "animal:cat,dog"
        with pytest.raises(ValueError, match="bird"):
            node.run(template, variables, 3, seed=0)

    def test_empty_variables_with_no_placeholders(self):
        """Template with no placeholders and empty variables should work."""
        node = PSN_Prompt_Generator()
        template = "a simple prompt"
        variables = ""
        result = node.run(template, variables, 3, seed=0)
        prompts = result[0]
        assert len(prompts) == 3
        assert all(p == "a simple prompt" for p in prompts)

    def test_single_variation(self):
        """num_variations=1 should produce exactly one prompt."""
        node = PSN_Prompt_Generator()
        template = "a {x}"
        variables = "x:one,two"
        result = node.run(template, variables, 1, seed=7)
        prompts = result[0]
        assert len(prompts) == 1
        assert prompts[0] in ("a one", "a two")


class TestPSN_Prompt_Iterator:
    def test_basic_iteration(self):
        """Iterate through prompts one at a time."""
        node = PSN_Prompt_Iterator()
        prompts_text = "first prompt\nsecond prompt\nthird prompt"
        # Index 0
        prompt, next_idx, done = node.run(prompts_text, 0)
        assert prompt == "first prompt"
        assert next_idx == 1
        assert done is False
        # Index 1
        prompt, next_idx, done = node.run(prompts_text, 1)
        assert prompt == "second prompt"
        assert next_idx == 2
        assert done is False
        # Index 2
        prompt, next_idx, done = node.run(prompts_text, 2)
        assert prompt == "third prompt"
        assert next_idx == 3
        assert done is True

    def test_done_at_end(self):
        """Index at or beyond the last prompt should report done."""
        node = PSN_Prompt_Iterator()
        prompts_text = "only one"
        prompt, next_idx, done = node.run(prompts_text, 1)
        assert prompt == ""
        assert done is True

    def test_empty_prompts(self):
        """Empty prompts string should report done immediately."""
        node = PSN_Prompt_Iterator()
        prompt, next_idx, done = node.run("", 0)
        assert prompt == ""
        assert next_idx == 0
        assert done is True

    def test_whitespace_only_prompts(self):
        """Whitespace-only prompts should be treated as empty."""
        node = PSN_Prompt_Iterator()
        prompt, next_idx, done = node.run("   \n  \n", 0)
        assert prompt == ""
        assert done is True

    def test_index_beyond_range(self):
        """Index beyond the number of prompts should report done."""
        node = PSN_Prompt_Iterator()
        prompts_text = "a\nb"
        prompt, next_idx, done = node.run(prompts_text, 10)
        assert prompt == ""
        assert done is True

    def test_single_prompt(self):
        """Single prompt: index 0 yields it, index 1 is done."""
        node = PSN_Prompt_Iterator()
        prompts_text = "the only prompt"
        prompt, next_idx, done = node.run(prompts_text, 0)
        assert prompt == "the only prompt"
        assert next_idx == 1
        assert done is True
        prompt, next_idx, done = node.run(prompts_text, 1)
        assert prompt == ""
        assert done is True
