"""Tests for h_verify_the_integrity_of_user_uploa."""

import torch

from h_verify_the_integrity_of_user_uploa import (
    PSN_ComputeMediaHash,
    PSN_VerifyMediaIntegrity,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    compute_hash,
    verify,
    _extract_tensor,
    _fnv1a64,
)

# --- 1. FNV-1a basic sanity: known 64-bit FNV-1a of empty string ---
assert _fnv1a64(b"") == "cbf29ce484222325", "FNV-1a of empty string mismatch"

# --- 2. Deterministic hash for a small IMAGE tensor ---
img = torch.zeros(1, 4, 4, 3, dtype=torch.float32)
h1 = compute_hash(img)
h2 = compute_hash(img)
assert h1 == h2, "Hash must be deterministic"
assert len(h1) == 16, f"Hash should be 16 hex chars, got {len(h1)}"

# --- 3. Different tensors produce different hashes ---
img2 = torch.ones(1, 4, 4, 3, dtype=torch.float32)
assert compute_hash(img) != compute_hash(img2), "Different tensors must hash differently"

# --- 4. Verify returns True for matching hash, False for wrong hash ---
assert verify(img, h1) is True, "verify should pass for correct hash"
assert verify(img, "0" * 16) is False, "verify should fail for wrong hash"

# --- 5. Case-insensitive hash comparison ---
assert verify(img, h1.upper()) is True, "Hash comparison should be case-insensitive"

# --- 6. LATENT dict payload ---
latent = {"samples": torch.randn(1, 4, 8, 8, dtype=torch.float32)}
latent_hash = compute_hash(latent)
assert len(latent_hash) == 16
assert verify(latent, latent_hash) is True

# --- 7. MASK (3-D) payload ---
mask = torch.zeros(1, 4, 4, dtype=torch.float32)
mask_hash = compute_hash(mask)
assert len(mask_hash) == 16
assert verify(mask, mask_hash) is True

# --- 8. Bad input: empty attested_hash raises ValueError ---
try:
    verify(img, "")
    assert False, "Expected ValueError for empty attested_hash"
except ValueError:
    pass

# --- 9. Bad input: non-string attested_hash raises ValueError ---
try:
    verify(img, 12345)
    assert False, "Expected ValueError for non-string attested_hash"
except ValueError:
    pass

# --- 10. Bad input: unsupported tensor dim raises ValueError ---
try:
    _extract_tensor(torch.randn(2, dtype=torch.float32))
    assert False, "Expected ValueError for 1-D tensor"
except ValueError:
    pass

# --- 11. Bad input: dict without 'samples' raises ValueError ---
try:
    _extract_tensor({"foo": 1})
    assert False, "Expected ValueError for dict without 'samples'"
except ValueError:
    pass

# --- 12. Node class structure checks ---
assert "PSN_VerifyMediaIntegrity" in NODE_CLASS_MAPPINGS
assert "PSN_ComputeMediaHash" in NODE_CLASS_MAPPINGS
assert "PSN_VerifyMediaIntegrity" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_ComputeMediaHash" in NODE_DISPLAY_NAME_MAPPINGS

node = PSN_VerifyMediaIntegrity()
assert node.FUNCTION == "run"
assert node.CATEGORY == "ParametricStudio/Integrity"
assert node.RETURN_TYPES == ("BOOLEAN", "STRING")
assert node.RETURN_NAMES == ("integrity_ok", "computed_hash")

# --- 13. Node run: correct hash passes ---
ok, computed = node.run(img, h1)
assert ok is True
assert computed == h1

# --- 14. Node run: wrong hash fails ---
ok2, _ = node.run(img, "f" * 16)
assert ok2 is False

# --- 15. ComputeMediaHash node ---
hash_node = PSN_ComputeMediaHash()
(computed2,) = hash_node.run(img)
assert computed2 == h1

# --- 16. Inputs are not mutated in place ---
img_orig = img.clone()
_ = node.run(img, h1)
assert torch.equal(img, img_orig), "Input tensor must not be mutated"

print("ok")
