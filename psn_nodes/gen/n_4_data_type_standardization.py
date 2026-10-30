"""ParametricStudio – Data Type Standardization nodes.

Converts and manipulates primitive data types to ensure consistent input
formats for downstream ComfyUI nodes.
"""

CAT = "ParametricStudio/Data"


class PSN_StringToList:
    """Split a string into a list of strings using a delimiter."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_input": ("STRING", {"default": ""}),
                "delimiter": ("STRING", {"default": ","}),
            }
        }

    RETURN_TYPES = ("LIST[STRING]",)
    RETURN_NAMES = ("list_output",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, string_input, delimiter):
        if string_input is None:
            string_input = ""
        if delimiter is None:
            delimiter = ","
        if string_input == "":
            return ([],)
        parts = string_input.split(delimiter)
        return (parts,)


class PSN_ListToString:
    """Join a list of strings into a single string using a delimiter."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_input": ("LIST[STRING]",),
                "delimiter": ("STRING", {"default": ","}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string_output",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, list_input, delimiter):
        if list_input is None:
            list_input = []
        if delimiter is None:
            delimiter = ","
        # Ensure every element is a string
        items = [str(x) for x in list_input]
        return (delimiter.join(items),)


class PSN_IntToFloatList:
    """Convert a list of integers to a list of floats."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "int_list": ("LIST[INT]",),
            }
        }

    RETURN_TYPES = ("LIST[FLOAT]",)
    RETURN_NAMES = ("float_list",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, int_list):
        if int_list is None:
            int_list = []
        result = []
        for i, v in enumerate(int_list):
            try:
                result.append(float(v))
            except (TypeError, ValueError):
                raise ValueError(
                    f"int_list element at index {i} is not numeric: {v!r}"
                )
        return (result,)


NODE_CLASS_MAPPINGS = {
    "PSN_StringToList": PSN_StringToList,
    "PSN_ListToString": PSN_ListToString,
    "PSN_IntToFloatList": PSN_IntToFloatList,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StringToList": "PSN String to List",
    "PSN_ListToString": "PSN List to String",
    "PSN_IntToFloatList": "PSN Int to Float List",
}
