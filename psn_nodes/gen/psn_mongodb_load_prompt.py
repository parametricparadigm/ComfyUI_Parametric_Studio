"""PSN_MongoDB_Load_Prompt (pure-logic, secure-by-design).

This module implements the *logic* of a "load prompt from MongoDB" node
without any real database, network, file, or OS access.  The spec's
`db_session` (MONGO_SESSION) is represented as a plain JSON text string
holding a mapping of document id -> document, and the "fetch" is a pure
in-memory lookup.  This keeps the node testable with the standard library
only and safe by design (no sockets, no pymongo, no I/O).

Inputs:
    db_session (STRING): JSON text mapping doc_id -> {"prompt": str, "params": dict}
    doc_id     (STRING): the id of the document to fetch

Outputs:
    prompt (STRING): the stored prompt text ("" if missing)
    params (STRING): the stored params serialized as JSON ("" if missing)
    found  (BOOLEAN): whether the document was found
    reason (STRING): human-readable status / error message
"""

import json

CAT = "ParametricStudio/Database"


def _parse_db_session(db_session):
    """Parse the db_session JSON text into a dict.

    Returns (data, error).  On success error is None and data is a dict.
    On failure data is None and error is a descriptive string.
    """
    if not isinstance(db_session, str):
        return None, "db_session must be a JSON string"
    text = db_session.strip()
    if not text:
        return None, "db_session is empty"
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        return None, "db_session is not valid JSON: %s" % exc
    if not isinstance(data, dict):
        return None, "db_session must be a JSON object mapping id -> document"
    return data, None


def _fetch_document(data, doc_id):
    """Fetch a document by id from the parsed mapping.

    Returns (doc, error).  doc is the stored document (a dict) or None.
    """
    if not isinstance(doc_id, str):
        return None, "doc_id must be a string"
    if doc_id not in data:
        return None, "document not found: %s" % doc_id
    doc = data[doc_id]
    if not isinstance(doc, dict):
        return None, "document for %s is not an object" % doc_id
    return doc, None


def _extract_prompt(doc):
    prompt = doc.get("prompt", "")
    if not isinstance(prompt, str):
        prompt = str(prompt)
    return prompt


def _extract_params(doc):
    params = doc.get("params", {})
    if not isinstance(params, (dict, list)):
        params = {"value": params}
    try:
        return json.dumps(params, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps({"value": str(params)}, sort_keys=True)


class PSN_MongoDB_Load_Prompt:
    """Fetch a saved prompt document by id from a JSON-encoded session."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_session": ("STRING", {"default": "{}", "multiline": True}),
                "doc_id": ("STRING", {"default": ""}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("prompt", "params", "found", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, db_session, doc_id):
        data, err = _parse_db_session(db_session)
        if err is not None:
            return ("", "", False, err)

        doc, err = _fetch_document(data, doc_id)
        if err is not None:
            return ("", "", False, err)

        prompt = _extract_prompt(doc)
        params = _extract_params(doc)
        return (prompt, params, True, "ok")


NODE_CLASS_MAPPINGS = {"PSN_MongoDB_Load_Prompt": PSN_MongoDB_Load_Prompt}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_MongoDB_Load_Prompt": "PSN MongoDB Load Prompt"}
