"""Tests for PSN_CSV_Batch_Prompter node."""

import json
import pytest
from psn_nodes.gen.psn_csv_batch_prompter import PSN_CSV_Batch_Prompter, _parse_csv_text, _batch_list


class TestPSN_CSV_Batch_Prompter:
    """Test suite for the CSV Batch Prompter node."""
    
    def test_basic_three_rows(self):
        """Test parsing a simple CSV with 3 rows."""
        csv_text = """positive,negative
A cat sitting on a mat,blurry
A dog running in a field,low quality
A bird flying in the sky,ugly"""
        
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text=csv_text,
            positive_col="positive",
            negative_col="negative",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        ref_images = json.loads(ref_images_json)
        
        assert row_count == 3
        assert prompts == ["A cat sitting on a mat", "A dog running in a field", "A bird flying in the sky"]
        assert negatives == ["blurry", "low quality", "ugly"]
        assert ref_images == []
    
    def test_with_ref_image_column(self):
        """Test parsing CSV with a reference image column."""
        csv_text = """positive,negative,ref_image
Prompt one,Neg one,/path/to/img1.png
Prompt two,Neg two,/path/to/img2.png"""
        
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text=csv_text,
            positive_col="positive",
            negative_col="negative",
            batch_size=2,
            ref_image_col="ref_image"
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        ref_images = json.loads(ref_images_json)
        
        assert row_count == 2
        assert prompts == ["Prompt one", "Prompt two"]
        assert negatives == ["Neg one", "Neg two"]
        assert ref_images == ["/path/to/img1.png", "/path/to/img2.png"]
    
    def test_missing_values_use_defaults(self):
        """Test that missing values are replaced with defaults."""
        csv_text = """positive,negative
A valid prompt,
Another valid prompt,
Third valid prompt,""
"""
        
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text=csv_text,
            positive_col="positive",
            negative_col="negative",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        
        assert row_count == 3
        assert prompts == ["A valid prompt", "Another valid prompt", "Third valid prompt"]
        assert negatives == ["", "", ""]
    
    def test_empty_csv_text(self):
        """Test handling of empty CSV text."""
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text="",
            positive_col="positive",
            negative_col="negative",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        ref_images = json.loads(ref_images_json)
        
        assert row_count == 0
        assert prompts == []
        assert negatives == []
        assert ref_images == []
    
    def test_whitespace_only_csv(self):
        """Test handling of whitespace-only CSV text."""
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text="   \n  \n  ",
            positive_col="positive",
            negative_col="negative",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        
        assert row_count == 0
        assert prompts == []
        assert negatives == []
    
    def test_missing_column_names(self):
        """Test that missing column names default to empty strings."""
        csv_text = """col_a,col_b
value1,value2
value3,value4"""
        
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text=csv_text,
            positive_col="nonexistent_col",
            negative_col="another_missing",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        
        assert row_count == 2
        assert prompts == ["", ""]
        assert negatives == ["", ""]
    
    def test_batch_list_function(self):
        """Test the _batch_list helper function."""
        lst = [1, 2, 3, 4, 5, 6, 7]
        
        batches = _batch_list(lst, 3)
        assert batches == [[1, 2, 3], [4, 5, 6], [7]]
        
        batches = _batch_list(lst, 2)
        assert batches == [[1, 2], [3, 4], [5, 6], [7]]
        
        batches = _batch_list(lst, 10)
        assert batches == [[1, 2, 3, 4, 5, 6, 7]]
        
        batches = _batch_list([], 3)
        assert batches == []
    
    def test_invalid_batch_size_defaults_to_one(self):
        """Test that invalid batch_size values are handled gracefully."""
        csv_text = """positive,negative
A,B
C,D"""
        
        node = PSN_CSV_Batch_Prompter()
        # batch_size is validated by ComfyUI to be >= 1, but test the helper
        batches = _batch_list([1, 2, 3], 0)
        assert batches == [[1], [2], [3]]
        
        batches = _batch_list([1, 2, 3], -1)
        assert batches == [[1], [2], [3]]
    
    def test_csv_with_quoted_fields(self):
        """Test parsing CSV with quoted fields containing commas."""
        csv_text = """positive,negative
"A cat, sitting on a mat",blurry
"A dog, running in a field","low quality, blurry"
"""
        
        node = PSN_CSV_Batch_Prompter()
        prompts_json, negatives_json, ref_images_json, row_count = node.run(
            csv_text=csv_text,
            positive_col="positive",
            negative_col="negative",
            batch_size=1
        )
        
        prompts = json.loads(prompts_json)
        negatives = json.loads(negatives_json)
        
        assert row_count == 2
        assert prompts == ["A cat, sitting on a mat", "A dog, running in a field"]
        assert negatives == ["blurry", "low quality, blurry"]
    
    def test_parse_csv_text_directly(self):
        """Test the _parse_csv_text helper function directly."""
        csv_text = """pos,neg,ref
Hello,World,/img1.png
Hi,There,/img2.png"""
        
        prompts, negatives, refs = _parse_csv_text(csv_text, "pos", "neg", "ref")
        
        assert prompts == ["Hello", "Hi"]
        assert negatives == ["World", "There"]
        assert refs == ["/img1.png", "/img2.png"]
    
    def test_node_class_mappings_exist(self):
        """Test that module-level mappings are correctly defined."""
        from psn_nodes.gen import psn_csv_batch_prompter
        
        assert "PSN_CSV_Batch_Prompter" in psn_csv_batch_prompter.NODE_CLASS_MAPPINGS
        assert "PSN_CSV_Batch_Prompter" in psn_csv_batch_prompter.NODE_DISPLAY_NAME_MAPPINGS
        assert psn_csv_batch_prompter.NODE_CLASS_MAPPINGS["PSN_CSV_Batch_Prompter"] == PSN_CSV_Batch_Prompter
