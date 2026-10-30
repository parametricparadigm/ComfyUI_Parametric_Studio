"""PSN_Data_Getter: Retrieves data from a named global variable.

This module implements a pure-logic, secure-by-design data getter node for ComfyUI.
It reads from a module-level global dictionary (simulating ComfyUI's global state)
and returns the stored value or a default if not found.

No file I/O, network, subprocess, or GPU operations are performed.
The global dictionary is in-memory only and resets on module reload.
"""

# Module-level global dictionary to simulate ComfyUI's global data store
_PSN_GLOBAL_DATA = {}

# Category for this node
CAT = "ParametricStudio/Data"

# Placeholder for ComfyUI's ANY type (not available in pure Python stdlib)
ANY = "ANY"


class PSN_Data_Getter:
    """Retrieves data from a named global variable.

    If the named slot exists in the global data store, returns its value.
    Otherwise, returns the provided default value.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "default": (ANY,),
            },
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("data",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, name, default=None):
        """Retrieve data from the global dictionary by name.

        Args:
            name: The name of the data slot to retrieve.
            default: The value to return if the slot is not found.

        Returns:
            A tuple containing the retrieved data (or default if not found).
        """
        if isinstance(name, str) and name in _PSN_GLOBAL_DATA:
            return (_PSN_GLOBAL_DATA[name],)
        return (default,)


# Helper function to set data in the global dictionary (for testing and PSN_Data_Setter)
def psn_set_global_data(name, value):
    """Set a value in the global data dictionary.

    Args:
        name: The name of the data slot.
        value: The value to store.
    """
    if isinstance(name, str):
        _PSN_GLOBAL_DATA[name] = value


# Helper function to clear all global data (for testing)
def psn_clear_global_data():
    """Clear all data from the global dictionary."""
    _PSN_GLOBAL_DATA.clear()


# Node mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "PSN_Data_Getter": PSN_Data_Getter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Data_Getter": "PSN Data Getter",
}
