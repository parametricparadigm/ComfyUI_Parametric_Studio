"""PSN_CSV_Batch_Prompter: parse CSV text into prompt batches.

This module implements the pure-logic, secure-by-design part of a CSV batch
prompter. It does NOT open files, sockets, or perform any OS/network I/O.
Instead, it accepts CSV content as a plain string (JSON text or raw CSV text)
and parses it using the standard library `csv` module.

Inputs are plain values (strings, numbers). The node is designed to be fed
CSV text from an upstream node that handles file I/O, or from a user pasting
CSV content directly.

Dependencies: Python standard library only (csv, json).
"""

import csv
import io
import json

# Category for the node
CAT = "ParametricStudio/CSV"

# Default values for missing columns
DEFAULT_POSITIVE = ""
DEFAULT_NEGATIVE = ""
DEFAULT_REF_IMAGE = ""


def _parse_csv_text(csv_text, positive_col, negative_col, ref_image_col=None):
    """
    Parse CSV text and extract specified columns.
    
    Args:
        csv_text: Raw CSV content as a string.
        positive_col: Column name for positive prompts.
        negative_col: Column name for negative prompts.
        ref_image_col: Optional column name for reference image paths.
    
    Returns:
        Tuple of (prompts, negatives, ref_images) where each is a list of strings.
    """
    if not csv_text or not csv_text.strip():
        return [], [], []
    
    # Use csv.DictReader to parse the CSV
    reader = csv.DictReader(io.StringIO(csv_text))
    
    prompts = []
    negatives = []
    ref_images = []
    
    for row in reader:
        # Get positive prompt with default
        pos = row.get(positive_col, DEFAULT_POSITIVE)
        if pos is None:
            pos = DEFAULT_POSITIVE
        prompts.append(pos.strip())
        
        # Get negative prompt with default
        neg = row.get(negative_col, DEFAULT_NEGATIVE)
        if neg is None:
            neg = DEFAULT_NEGATIVE
        negatives.append(neg.strip())
        
        # Get reference image path if column specified
        if ref_image_col:
            ref = row.get(ref_image_col, DEFAULT_REF_IMAGE)
            if ref is None:
                ref = DEFAULT_REF_IMAGE
            ref_images.append(ref.strip())
    
    return prompts, negatives, ref_images


def _batch_list(lst, batch_size):
    """
    Split a list into batches of the given size.
    
    Args:
        lst: The list to batch.
        batch_size: Number of items per batch.
    
    Returns:
        List of lists, each containing up to batch_size items.
    """
    if batch_size <= 0:
        batch_size = 1
    return [lst[i:i + batch_size] for i in range(0, len(lst), batch_size)]


class PSN_CSV_Batch_Prompter:
    """
    Parse CSV text into batches of prompts, negatives, and reference image paths.
    
    This node accepts CSV content as a string and parses it into lists that
    can be fed into a loop or batch sampler. It handles missing values by
    using defaults.
    
    Note: This node does NOT read files. Feed it CSV text from an upstream
    node that handles file I/O, or paste CSV content directly.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "csv_text": ("STRING", {"default": "", "multiline": True}),
                "positive_col": ("STRING", {"default": "positive"}),
                "negative_col": ("STRING", {"default": "negative"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 10000, "step": 1}),
            },
            "optional": {
                "ref_image_col": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    RETURN_NAMES = ("prompts_json", "negatives_json", "ref_images_json", "row_count")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, csv_text, positive_col, negative_col, batch_size, ref_image_col=None):
        """
        Parse CSV text and return JSON-serialized lists of prompts, negatives,
        and reference image paths, along with the total row count.
        
        Args:
            csv_text: Raw CSV content as a string.
            positive_col: Column name for positive prompts.
            negative_col: Column name for negative prompts.
            batch_size: Number of rows per batch (informational; full list returned).
            ref_image_col: Optional column name for reference image paths.
        
        Returns:
            Tuple of (prompts_json, negatives_json, ref_images_json, row_count)
            where each *_json is a JSON array string.
        """
        # Validate column names
        if not positive_col or not positive_col.strip():
            positive_col = "positive"
        if not negative_col or not negative_col.strip():
            negative_col = "negative"
        
        # Parse CSV
        prompts, negatives, ref_images = _parse_csv_text(
            csv_text, positive_col, negative_col, ref_image_col
        )
        
        # Serialize to JSON for transport
        prompts_json = json.dumps(prompts)
        negatives_json = json.dumps(negatives)
        ref_images_json = json.dumps(ref_images)
        
        row_count = len(prompts)
        
        return (prompts_json, negatives_json, ref_images_json, row_count)


# Module-level mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_CSV_Batch_Prompter": PSN_CSV_Batch_Prompter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CSV_Batch_Prompter": "CSV Batch Prompter"
}
