"""Free-service connectors: model catalogues (Civitai, Hugging Face) and, later, free remote generation. Every connector is opt-in, SFW-only, read-first, and takes its token from an
environment variable (never from a file we print, never in a URL). Downloads need an explicit confirm and are hash-checked against what the service reported."""
