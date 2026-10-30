# CU-221 - Caching: why changing the seed does not reload the model

**Objective.** Work out which nodes rerun after any edit, and choose a cache policy knowing what it trades. Taught by Captain Graph.

## The idea

Each node gets a key made from its class, its constant inputs and, recursively, the same data for all its ancestors. If a key was seen and its result is still held, the node does not run. The key depends on what would be computed, not on where the node sits on the canvas.

## The mechanism

`CacheKeySetInputSignature` in `comfy_execution/caching.py` builds the signature. For the node and each ancestor it records:

- the class type, and the value from `fingerprint_inputs` (V3) or `IS_CHANGED` (older nodes), held in `IsChangedCache`
- each input in sorted order: a constant as itself, a link as ("ANCESTOR", ancestor index, output slot)
- the node id too, but only for `NOT_IDEMPOTENT` nodes and nodes taking `UNIQUE_ID`

Since links are numbered by position in the ancestry, renaming every node changes nothing. A `float("NaN")` fingerprint means "always run", because NaN never equals itself. `to_hashable` also turns anything it cannot hash into an `Unhashable` object, which never matches either. Note that `IsChangedCache` passes `execution_list=None`, so a fingerprint function sees constants and not linked values.

`main.py` chooses the policy, and `CacheSet` builds it:

| Flag | Class | Behaviour |
|---|---|---|
| none (default) | `RAMPressureCache` | Keeps results, evicting by age and size when free RAM runs low |
| `--cache-classic` | `HierarchicalCache` | Drops anything the current prompt does not use |
| `--cache-lru N` | `LRUCache` | Evicts the least recently used generations above N results |
| `--cache-none` | `NullCache` | Runs every node every time |

## Lab

```text
first run          ran: ['ckpt', 'pos', 'neg', 'lat', 'smp', 'dec', 'out']
same graph again   ran: []
seed changed       ran: ['smp', 'dec', 'out']
prompt changed     ran: ['pos', 'smp', 'dec', 'out']
all ids renamed    ran: []
```

The seed row is the title of this lesson: the sampler and all that follows it run again, and the loader does not.

```text
file unchanged     ran: []
file edited on disk ran: ['f', 'out']
same inputs, not_idempotent, two nodes: keys equal? False
same inputs, ordinary node, two nodes: keys equal? True
```

The last line is a real effect: two identical ordinary nodes share one result.

```text
policy         nodes run over A B A B   (7 per full run)
classic        16
lru 100        10
lru 4          16
none           28
```

Alternating between two prompts is where policy matters. Classic forgets the other prompt each time, and a large LRU remembers both. The lab's LRU counts single results, while the real one evicts by generation, so read this for the direction. RAM pressure, the default, is not simulated because its behaviour depends on free RAM on the machine.

## What goes wrong

A node with hidden state, such as reading a clock or a file with no fingerprint, returns a stale result, because the key cannot see that state. See CU-401.

## Sources

- [ComfyUI v0.43.0, comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/caching.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, main.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/main.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
