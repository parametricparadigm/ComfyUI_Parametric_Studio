"""PSN_Dynamic_Model_Selector: resolve a model checkpoint path from a list of candidates.

This module implements a pure-logic ComfyUI custom node that selects a model
checkpoint based on a key/value pair, simulating the behavior of reading from
an external source (like a spreadsheet) without performing any actual I/O.

The node takes a list of model identifiers (paths or names), a selector key
(which is used for context/logging but the matching is primarily on the value),
and a selector value. It searches the list for a match.

Security & Design:
- No file system access is performed. The "paths" are treated as opaque strings.
- No network calls.
- Pure Python standard library only.
- Safe by design: if no match is found, it returns a safe fallback or raises
  a controlled error depending on configuration, rather than crashing the
  entire ComfyUI process unexpectedly.

Inputs:
- model_list (LIST): List of available model paths/names.
- selector_key (STRING): The key from the external data (e.g., "model_name").
- selector_value (STRING): The value to match (e.g., "sdxl_base").
- match_mode (STRING): "exact", "case_insensitive", or "contains".
- on_missing (STRING): "error", "first", or "empty".

Outputs:
- model_path (STRING): The resolved path to the model.
- model_name (STRING): The name of the selected model (derived from path).
- matched (BOOLEAN): Whether a match was found.
- reason (STRING): Explanation of the selection outcome.
"""

# We assume 'psn' module is available in the ComfyUI environment for shared utilities.
# If not, we define minimal local helpers to keep the node self-contained for testing.
try:
    from psn import expr, orchestration
except ImportError:
    # Fallback for standalone testing or if psn module is not fully set up
    class _MockOrchestration:
        @staticmethod
        def gate(score, threshold, mode):
            # Simple gate logic for compatibility if needed, though not used here directly
            if mode == "gte":
                return score >= threshold, "score >= threshold"
            elif mode == "lte":
                return score <= threshold, "score <= threshold"
            else:
                return score == threshold, "score == threshold"
    
    orchestration = _MockOrchestration()
    expr = None

CAT = "ParametricStudio/Model"

# Allowed match modes
MATCH_MODES = ["exact", "case_insensitive", "contains"]
# Allowed behaviors when no match is found
ON_MISSING_MODES = ["error", "first", "empty"]


def _extract_model_name(path_str):
    """Extract the model name from a path string.
    
    Handles both Unix and Windows path separators.
    Removes common model extensions (.safetensors, .ckpt, .pt, .bin) for cleaner names.
    """
    if not path_str:
        return ""
    
    # Normalize path separators
    normalized = path_str.replace("\\", "/")
    
    # Get the last component
    parts = normalized.split("/")
    name = parts[-1] if parts else normalized
    
    # Remove common extensions
    for ext in [".safetensors", ".ckpt", ".pt", ".bin", ".pth"]:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break
    
    return name


def _find_model(model_list, selector_value, match_mode):
    """Search the model list for a match based on the selector value and mode.
    
    Args:
        model_list: List of model path/name strings.
        selector_value: The value to search for.
        match_mode: One of "exact", "case_insensitive", "contains".
        
    Returns:
        Tuple of (matched_path, matched_name, reason)
    """
    if not model_list:
        return None, None, "Model list is empty"
    
    if not selector_value:
        return None, None, "Selector value is empty"
    
    # Ensure model_list is a list of strings
    valid_models = []
    for item in model_list:
        if isinstance(item, str):
            valid_models.append(item)
        elif isinstance(item, (list, tuple)) and len(item) > 0:
            # Handle case where list items might be tuples (e.g., (path, name))
            valid_models.append(str(item[0]))
        else:
            valid_models.append(str(item))
    
    if not valid_models:
        return None, None, "No valid model entries in list"
    
    matched_path = None
    matched_name = None
    reason = ""
    
    if match_mode == "exact":
        for path in valid_models:
            if path == selector_value:
                matched_path = path
                matched_name = _extract_model_name(path)
                reason = f"Exact match found: {path}"
                break
            # Also check if the extracted name matches exactly
            name = _extract_model_name(path)
            if name == selector_value:
                matched_path = path
                matched_name = name
                reason = f"Exact name match found: {path}"
                break
        
        if matched_path is None:
            reason = f"No exact match for '{selector_value}'"
            
    elif match_mode == "case_insensitive":
        target_lower = selector_value.lower()
        for path in valid_models:
            if path.lower() == target_lower:
                matched_path = path
                matched_name = _extract_model_name(path)
                reason = f"Case-insensitive match found: {path}"
                break
            name = _extract_model_name(path)
            if name.lower() == target_lower:
                matched_path = path
                matched_name = name
                reason = f"Case-insensitive name match found: {path}"
                break
        
        if matched_path is None:
            reason = f"No case-insensitive match for '{selector_value}'"
            
    elif match_mode == "contains":
        target_lower = selector_value.lower()
        for path in valid_models:
            if target_lower in path.lower():
                matched_path = path
                matched_name = _extract_model_name(path)
                reason = f"Contains match found: {path}"
                break
            name = _extract_model_name(path)
            if target_lower in name.lower():
                matched_path = path
                matched_name = name
                reason = f"Contains name match found: {path}"
                break
        
        if matched_path is None:
            reason = f"No contains match for '{selector_value}'"
            
    else:
        reason = f"Unknown match mode: {match_mode}"
    
    return matched_path, matched_name, reason


class PSN_Dynamic_Model_Selector:
    """Selects a model checkpoint based on a parameter from an external source.
    
    This node resolves a model path from a list of candidates by matching
    a selector value. It supports exact, case-insensitive, and contains
    matching modes. If no match is found, it can raise an error, return
    the first model, or return an empty string.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_list": ("LIST", {"default": []}),
                "selector_key": ("STRING", {"default": "model_name", "multiline": False}),
                "selector_value": ("STRING", {"default": "", "multiline": False}),
                "match_mode": (MATCH_MODES, {"default": "exact"}),
                "on_missing": (ON_MISSING_MODES, {"default": "error"}),
            },
            "optional": {
                "default_model": ("STRING", {"default": "", "multiline": False}),
            },
        }
    
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("model_path", "model_name", "matched", "reason")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, model_list, selector_key, selector_value, match_mode, on_missing, default_model=""):
        """Execute the model selection logic.
        
        Args:
            model_list: List of model paths/names.
            selector_key: The key from external data (for context).
            selector_value: The value to match against.
            match_mode: Matching strategy.
            on_missing: Behavior when no match is found.
            default_model: Optional default model to use if on_missing is "first" 
                          and no match is found, or as a fallback.
        
        Returns:
            Tuple of (model_path, model_name, matched, reason)
        """
        # Validate inputs
        if not isinstance(model_list, (list, tuple)):
            raise ValueError("model_list must be a list or tuple")
        
        if not isinstance(selector_key, str):
            raise ValueError("selector_key must be a string")
        
        if not isinstance(selector_value, str):
            raise ValueError("selector_value must be a string")
        
        if match_mode not in MATCH_MODES:
            raise ValueError(f"match_mode must be one of {MATCH_MODES}")
        
        if on_missing not in ON_MISSING_MODES:
            raise ValueError(f"on_missing must be one of {ON_MISSING_MODES}")
        
        # Perform the search
        matched_path, matched_name, reason = _find_model(model_list, selector_value, match_mode)
        
        if matched_path is not None:
            return (matched_path, matched_name, True, reason)
        
        # No match found - handle according to on_missing
        if on_missing == "error":
            raise ValueError(f"Model not found: {reason}. Key: '{selector_key}', Value: '{selector_value}'")
        
        elif on_missing == "first":
            if default_model:
                model_path = default_model
                model_name = _extract_model_name(default_model)
                reason = f"No match found. Using default model: {default_model}"
            elif model_list:
                # Use the first valid model from the list
                first_model = None
                for item in model_list:
                    if isinstance(item, str) and item:
                        first_model = item
                        break
                    elif isinstance(item, (list, tuple)) and len(item) > 0:
                        first_model = str(item[0])
                        break
                
                if first_model:
                    model_path = first_model
                    model_name = _extract_model_name(first_model)
                    reason = f"No match found. Using first model from list: {first_model}"
                else:
                    model_path = ""
                    model_name = ""
                    reason = "No match found and no models available in list"
            else:
                model_path = ""
                model_name = ""
                reason = "No match found and model list is empty"
            
            return (model_path, model_name, False, reason)
        
        elif on_missing == "empty":
            return ("", "", False, reason)
        
        else:
            raise ValueError(f"Unknown on_missing mode: {on_missing}")


# Node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Dynamic_Model_Selector": PSN_Dynamic_Model_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Dynamic_Model_Selector": "PSN Dynamic Model Selector",
}
