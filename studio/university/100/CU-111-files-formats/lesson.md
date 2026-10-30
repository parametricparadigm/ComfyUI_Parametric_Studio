# CU-111 - Files and formats: PNG metadata, MP4, WAV, safetensors

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

**Instructor:** Bit Bandit
**Course:** CU-111 (Foundations)
**Prerequisites:** None

## Why this matters

Welcome, students. I am Bit Bandit, and I live in the last few bits of your float32s. You think you’re just saving an image? No. You are writing a structured contract between your GPU and the rest of the universe.

In generative workflows, "reproducibility" is a lie unless the file format is structurally sound. A PNG is not just pixels; it is a container for metadata that tells the next person *how* those pixels were made. A `.safetensors` file is not just weights; it is a JSON header that maps memory addresses to tensor names. If the header is corrupt, the data is garbage. If the metadata is missing, the workflow is a black box.

This lesson covers the structural integrity of file headers. We will look at how ComfyUI injects workflow metadata into outgoing messages, how it hashes assets to ensure they haven’t been tampered with, and how it extracts lightweight headers without loading heavy data. We are here to ensure that when you press "Queue," the bits that leave your machine are exactly the bits you intended.

## The intuition

Think of a file format like a shipping container. The container has a rigid steel frame (the header) and a flexible cargo hold (the data).

1.  **The Header:** This is the manifest. It tells the receiver what’s inside, how big it is, and where to find it. In PNG, this is the `tEXt` or `iTXt` chunks. In `safetensors`, it is the JSON header at the start of the file.
2.  **The Data:** This is the cargo. The actual pixels, audio samples, or model weights.
3.  **The Checksum:** This is the seal on the container. If the seal is broken, the cargo might be tampered with. In our lab, we use a simple sum as a checksum. In real life, we use CRC32 or BLAKE3.

The key insight is that **metadata is embedded within standard formats**. It is not an afterthought. It is part of the structural integrity. If you strip the metadata from a PNG, you lose the prompt, the seed, and the workflow ID. You have pixels, but you have no history.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the math of integrity. We are dealing with binary data, but we need to verify it.

**1. The Checksum (Summation)**
In our lab, we compute a checksum $C$ for a tensor $T$ of shape $N \times M$.
$$ C = \sum_{i=1}^{N} \sum_{j=1}^{M} T_{ij} $$
Here, $T_{ij}$ is the value at row $i$, column $j$. This is a lightweight integrity check. If $C$ changes, the data changed. In real formats, we use cryptographic hashes like BLAKE3, which are one-way functions: $H(data) \rightarrow hash$. You cannot reverse $hash$ to get $data$, but you can verify that $data$ produces $hash$.

**2. The Header (JSON Serialization)**
The header is a dictionary $H$ containing key-value pairs.
$$ H = \{ k_1: v_1, k_2: v_2, \dots, k_n: v_n \} $$
This dictionary is serialized into a string $S$ using JSON.
$$ S = \text{JSON.dumps}(H) $$
The critical part is that $S$ must be valid JSON. If $H$ contains a non-serializable object, $S$ fails. In ComfyUI, `metadata_extract.py` reads these headers. For `safetensors`, it parses the JSON header without loading the weights. This is crucial for performance. You don’t want to load a 10GB model just to read its name.

**3. The Size Calculation**
The size of the data in bytes is:
$$ \text{size\_bytes} = \text{numel} \times \text{element\_size} $$
Where `numel` is the total number of elements ($N \times M$) and `element_size` is the bytes per element (4 for float32). This value is stored in the header so the reader knows how much memory to allocate.

## In ComfyUI (name real nodes/files/classes ONLY if they appear in the evidence; otherwise say 'not covered in our sources')

ComfyUI treats file formats as a service layer.

*   **`app/assets/services/metadata_extract.py`**: This module contains `extract_file_metadata` and `_read_safetensors_header`. The latter parses the safetensors JSON header without loading weights. This is the "lightweight header" reading I mentioned.
*   **`app/assets/services/hashing.py`**: Contains `compute_blake3_hash`. This is the cryptographic seal. It ensures that the file content matches the hash in the database.
*   **`tests-unit/server_test/test_ws_workflow_metadata.py`**: This test file validates how workflow metadata is injected into outgoing websocket messages. It ensures that `workflow_id` is extracted from client-provided PNG info. If the PNG has no `workflow_id`, the message is left unchanged. This is how ComfyUI tracks which workflow produced which image.
*   **`app/assets/services/ingest.py`**: The `ingest` function turns bytes into catalogued assets. It uses `snapshot_hash.py` to compute the BLAKE3 hash and ensures the file is stable during hashing.

Note: Specific node names for PNG writing are not covered in our sources, but the server-side metadata injection is well-documented in the tests.

## Lab (explain what the lab does, then quote 3-6 of its real `RESULT` lines exactly as printed and say what each proves)

The lab simulates a small data payload (a 4x4 float32 tensor) and creates a simple header structure. It computes a checksum (sum) and serializes the header to JSON. This mimics how PNG or WAV files embed metadata.

**Lab Output:**

1.  `RESULT checksum = -1.90911`
    *   **Proves:** The checksum is a finite number. This is a basic sanity check. If this were `NaN` or `inf`, the data would be corrupt. In real formats, this would be a CRC32 or BLAKE3 hash.

2.  `RESULT header_json = {"dtype": "torch.float32", "format": "SIMPLE_TENSOR", "shape": [4, 4], "size_bytes": 64}`
    *   **Proves:** The header is valid JSON. It contains the required fields: `dtype`, `format`, `shape`, and `size_bytes`. This is the "manifest" of the file. If this JSON were malformed, the reader would fail to parse the file.

3.  `RESULT size_bytes = 64`
    *   **Proves:** The size calculation is correct. $4 \times 4$ elements $\times$ 4 bytes per float32 = 64 bytes. This value is stored in the header so the reader knows how much memory to allocate.

## Common mistakes

1.  **Ignoring Metadata:** Saving a PNG without the `tEXt` chunks. You lose the prompt, seed, and workflow ID. The image is just pixels.
2.  **Corrupt Headers:** Modifying the JSON header of a `safetensors` file without updating the hash. The file will fail to load because the hash won’t match.
3.  **Non-Serializable Metadata:** Trying to put a Python object into the metadata dictionary. JSON can’t serialize it. The file will fail to write.
4.  **Assuming Reproducibility:** Thinking that if you have the same prompt and seed, you’ll get the same image. If the model file is corrupt (hash mismatch), you won’t.

## Go deeper (the papers in the evidence, by arXiv id)

*   **BLAKE3:** The hashing algorithm used in `app/assets/services/hashing.py`. While not an arXiv paper, BLAKE3 is a modern cryptographic hash function designed for speed. It is used to ensure content integrity.
*   **Safetensors:** The format used for model weights. It is a binary format with a JSON header. The header maps tensor names to their offsets and shapes in the binary data. This allows for safe loading without executing arbitrary code (unlike pickle).

Remember, students: The bits don’t lie, but they can be lost. Protect your headers.

