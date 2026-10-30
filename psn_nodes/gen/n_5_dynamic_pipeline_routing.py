"""ParametricStudio - Dynamic Pipeline Routing.

Routes an incoming API payload to one of several sub-workflow outputs
(video / music / image) based on a simple string match on `request_type`.

Design notes
------------
* Pure CPU / stdlib logic - no tensors are involved.
* The payload is passed through untouched (never mutated).
* Unknown / misspelled request types fall back to a configurable
  `default_route` so the pipeline can still make progress.
* The node also exposes a `routed_to` string output so downstream nodes
  can branch on which lane the payload was sent to.
"""

CAT = "ParametricStudio/Routing"

# Canonical lane names, in the order they appear on the node.
LANES = ("video", "music", "image")

# Sentinel used for "no payload" on the non-selected outputs.
# We use None because ComfyUI's ANY type accepts it and it is the
# natural "empty" value.
_EMPTY = None


def _normalize(request_type):
    """Lower-case, strip whitespace, collapse internal whitespace.

    Returns '' for non-string inputs so that bad input is handled
    gracefully instead of raising.
    """
    if not isinstance(request_type, str):
        return ""
    return " ".join(request_type.split()).lower()


class PSN_Request_Router:
    """Route a payload to the video / music / image lane by request type.

    Inputs
    ------
    request_type : str
        One of "video", "music", "image" (case-insensitive, whitespace
        tolerant).  Anything else is treated as unknown.
    payload : ANY
        The data to route.  Passed through unchanged.
    default_route : str
        Lane to use when `request_type` does not match any known lane.
        One of "video", "music", "image", "none".

    Outputs
    -------
    video_payload, music_payload, image_payload : ANY
        The payload on the selected lane, None on the others.
    routed_to : str
        The lane that actually received the payload ("none" if the
        default route was "none" and the type was unknown).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "request_type": ("STRING", {"default": "image"}),
                "payload": ("ANY",),
            },
            "optional": {
                "default_route": (
                    list(LANES) + ["none"],
                    {"default": "none"},
                ),
            },
        }

    RETURN_TYPES = ("ANY", "ANY", "ANY", "STRING")
    RETURN_NAMES = ("video_payload", "music_payload", "image_payload", "routed_to")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, request_type, payload, default_route="none"):
        lane = _normalize(request_type)
        if lane not in LANES:
            lane = _normalize(default_route) if default_route else "none"
            if lane not in LANES:
                lane = "none"

        # Build the three lane outputs; only the selected one carries
        # the payload, the rest are None.  We never mutate `payload`.
        video_payload = payload if lane == "video" else _EMPTY
        music_payload = payload if lane == "music" else _EMPTY
        image_payload = payload if lane == "image" else _EMPTY

        return (video_payload, music_payload, image_payload, lane)


NODE_CLASS_MAPPINGS = {
    "PSN_Request_Router": PSN_Request_Router,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Request_Router": "Request Router (Video/Music/Image)",
}
