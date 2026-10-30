import os
import sys
import shutil
import subprocess
import json
import platform

def _default_run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if result.returncode == 0:
            return result.stdout
        return ''
    except Exception:
        return ''

def _parse_meminfo(text):
    for line in text.splitlines():
        if line.startswith('MemTotal:'):
            parts = line.split()
            if len(parts) >= 2:
                kb = int(parts[1])
                return kb / (1024 * 1024)
    return 0.0

def detect(run=None, path='.'):
    if run is None:
        run = _default_run

    os_name = sys.platform
    if os_name.startswith('linux'):
        os_id = 'linux'
    elif os_name.startswith('win'):
        os_id = 'windows'
    elif os_name.startswith('darwin'):
        os_id = 'macos'
    else:
        os_id = 'linux'

    arch = platform.machine()
    cpu_cores = os.cpu_count() or 1

    ram_gb = 0.0
    if os_id == 'linux':
        try:
            with open('/proc/meminfo', 'r') as f:
                ram_gb = _parse_meminfo(f.read())
        except Exception:
            ram_gb = 0.0
    elif os_id == 'windows':
        out = run(['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'])
        try:
            ram_gb = int(out.strip()) / (1024 ** 3)
        except Exception:
            ram_gb = 0.0
    elif os_id == 'macos':
        out = run(['sysctl', '-n', 'hw.memsize'])
        try:
            ram_gb = int(out.strip()) / (1024 ** 3)
        except Exception:
            ram_gb = 0.0

    disk_free_gb = 0.0
    try:
        usage = shutil.disk_usage(path)
        disk_free_gb = usage.free / (1024 ** 3)
    except Exception:
        disk_free_gb = 0.0

    gpus = []
    backend = 'cpu'
    caps = []

    if os_id == 'linux' or os_id == 'windows':
        # Try NVIDIA
        out = run(['nvidia-smi', '--query-gpu=name,memory.total,compute_cap', '--format=csv,noheader,nounits'])
        if out:
            lines = out.strip().splitlines()
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    name = parts[0]
                    try:
                        vram_gb = float(parts[1]) / 1024.0
                    except ValueError:
                        vram_gb = 0.0
                    try:
                        cc_str = parts[2].replace('.', '')
                        cc = float(cc_str) / 10.0
                    except ValueError:
                        cc = None
                    
                    gpu = {
                        'vendor': 'nvidia',
                        'name': name,
                        'vram_gb': vram_gb,
                        'compute_cap': cc
                    }
                    gpus.append(gpu)
                    if backend == 'cpu':
                        backend = 'cuda'
                        if cc is not None:
                            if cc >= 8.0:
                                caps.append('bf16')
                            if cc >= 8.9:
                                caps.append('fp8')
                            if cc >= 10.0:
                                caps.append('nvfp4')
        
        # Try AMD if no NVIDIA found
        if not gpus:
            out = run(['rocm-smi', '--showproductname', '--showmeminfo', 'vram', '--json'])
            if out:
                try:
                    data = json.loads(out)
                    # Best effort parsing, structure varies
                    if isinstance(data, list):
                        for item in data:
                            name = item.get('card', {}).get('card_name', 'AMD GPU')
                            vram = item.get('card', {}).get('vram', {}).get('total', 0)
                            if vram:
                                gpus.append({
                                    'vendor': 'amd',
                                    'name': name,
                                    'vram_gb': vram / (1024 ** 3),
                                    'compute_cap': None
                                })
                                if backend == 'cpu':
                                    backend = 'rocm'
                except Exception:
                    pass

    elif os_id == 'macos':
        out = run(['sysctl', '-n', 'machdep.cpu.brand_string'])
        cpu_name = out.strip() if out else 'Apple Silicon'
        
        # Check for Apple Silicon (arm64)
        if arch == 'arm64' or 'Apple' in cpu_name:
            gpus.append({
                'vendor': 'apple',
                'name': cpu_name,
                'vram_gb': ram_gb,
                'compute_cap': None
            })
            backend = 'mps'

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return {
        'os': os_id,
        'arch': arch,
        'cpu_cores': cpu_cores,
        'ram_gb': ram_gb,
        'disk_free_gb': disk_free_gb,
        'gpus': gpus,
        'backend': backend,
        'caps': caps,
        'python': python_version
    }

def usable_vram_gb(profile, reserve_gb=2.0):
    gpus = profile.get('gpus', [])
    if not gpus:
        return 0.0
    
    best = 0.0
    for gpu in gpus:
        vram = gpu.get('vram_gb', 0.0)
        vendor = gpu.get('vendor', '')
        
        if vendor == 'apple':
            # Unified memory: 65% of RAM
            val = 0.65 * profile.get('ram_gb', 0.0) - reserve_gb
        else:
            val = vram - reserve_gb
        
        if val > best:
            best = val
            
    return max(0.0, best)

def plan(profile, manifest, goals=None, reserve_gb=2.0):
    usable = usable_vram_gb(profile, reserve_gb)
    ram_gb = profile.get('ram_gb', 0.0)
    caps = profile.get('caps', [])
    backend = profile.get('backend', 'cpu')
    
    items = []
    warnings = []
    seen_files = set()
    total_download_gb = 0.0
    
    models = manifest.get('models', [])
    
    # Filter models by goals if specified
    if goals is not None:
        models = [m for m in models if m.get('goal') in goals]

    for model in models:
        goal = model.get('goal', '')
        model_id = model.get('id', '')
        variants = model.get('variants', [])
        
        if not variants:
            continue
            
        # Sort variants by quality descending to pick the best one first
        sorted_variants = sorted(variants, key=lambda v: v.get('quality', 0), reverse=True)
        
        chosen_variant = None
        mode = 'unavailable'
        reason = ''
        comfy_flags = []
        
        for variant in sorted_variants:
            v_id = variant.get('id', '')
            v_label = variant.get('label', v_id)
            peak_vram = variant.get('peak_vram_gb', 0.0)
            offload_ok = variant.get('offload_ok', False)
            min_ram = variant.get('min_ram_gb', 0.0)
            needs = variant.get('needs', [])
            backends = variant.get('backends', [])
            
            # Check backend compatibility
            if backend not in backends:
                continue
                
            # Check capability needs
            if not all(need in caps for need in needs):
                continue
                
            # Check if it fits in GPU VRAM
            if peak_vram <= usable:
                chosen_variant = variant
                mode = 'gpu'
                reason = ''
                comfy_flags = []
                break
            else:
                # Check if offload is possible
                if offload_ok and ram_gb >= min_ram:
                    chosen_variant = variant
                    mode = 'offload'
                    reason = 'Will be slower due to offloading'
                    if usable < 0.25 * peak_vram:
                        comfy_flags = ['--novram']
                    else:
                        comfy_flags = ['--lowvram']
                    break
                else:
                    # Record reason for unavailable if this was the best candidate
                    # We continue to see if a lower quality variant fits? 
                    # Spec says: "For each goal pick the highest-quality variant whose needs are all in profile caps and whose backends contains profile backend and whose peak_vram_gb <= usable_vram -> mode 'gpu'. If none fits but a variant has offload_ok... -> mode 'offload'... else 'unavailable'"
                    # This implies we check variants in order of quality. If the highest quality doesn't fit GPU, we check if it can offload. If it can't offload, do we try the next one?
                    # "If none fits" usually implies checking all candidates for the 'gpu' condition. Then if no 'gpu' candidate, check for 'offload' candidates.
                    # Let's re-read carefully: "For each goal pick the highest-quality variant whose needs are all in profile caps and whose backends contains profile backend and whose peak_vram_gb <= usable_vram -> mode 'gpu' (flags []). If none fits but a variant has offload_ok and ram_gb >= min_ram_gb -> mode 'offload'..."
                    # This suggests:
                    # 1. Find all variants that are compatible (backend + caps).
                    # 2. Among those, find the highest quality one that fits in VRAM. If found -> GPU.
                    # 3. If no GPU fit, find the highest quality one that supports offload and has enough RAM. If found -> Offload.
                    # 4. Else -> Unavailable.
                    
                    pass # We handle this logic outside the loop or by collecting candidates

        # Re-implementing the selection logic more clearly based on spec interpretation
        compatible_variants = []
        for variant in sorted_variants:
            needs = variant.get('needs', [])
            backends = variant.get('backends', [])
            if backend in backends and all(need in caps for need in needs):
                compatible_variants.append(variant)
                
        chosen_variant = None
        mode = 'unavailable'
        reason = ''
        comfy_flags = []
        
        # 1. Try GPU
        for variant in compatible_variants:
            if variant.get('peak_vram_gb', 0.0) <= usable:
                chosen_variant = variant
                mode = 'gpu'
                reason = ''
                comfy_flags = []
                break
                
        # 2. Try Offload
        if mode != 'gpu':
            for variant in compatible_variants:
                if variant.get('offload_ok', False) and ram_gb >= variant.get('min_ram_gb', 0.0):
                    chosen_variant = variant
                    mode = 'offload'
                    reason = 'Will be slower due to offloading'
                    peak = variant.get('peak_vram_gb', 0.0)
                    if usable < 0.25 * peak:
                        comfy_flags = ['--novram']
                    else:
                        comfy_flags = ['--lowvram']
                    break
                    
        # 3. Unavailable
        if mode != 'gpu' and mode != 'offload':
            # Find the best compatible variant to explain why it failed
            if compatible_variants:
                best = compatible_variants[0]
                peak = best.get('peak_vram_gb', 0.0)
                if not best.get('offload_ok', False) or ram_gb < best.get('min_ram_gb', 0.0):
                    reason = f"needs {peak:.1f} GB, this machine has {usable:.1f} GB usable"
                else:
                    reason = "incompatible"
            else:
                reason = "no compatible variant"
                
        if chosen_variant:
            files = chosen_variant.get('files', [])
            download_gb = 0.0
            for f in files:
                key = (f.get('repo', ''), f.get('path', ''))
                if key not in seen_files:
                    seen_files.add(key)
                    download_gb += f.get('size_gb', 0.0)
            
            total_download_gb += download_gb
            
            items.append({
                'goal': goal,
                'model': model_id,
                'variant': chosen_variant.get('id', ''),
                'mode': mode,
                'reason': reason,
                'est_vram_gb': chosen_variant.get('peak_vram_gb', 0.0),
                'download_gb': download_gb,
                'comfy_flags': comfy_flags
            })
        else:
            # Even if unavailable, we might want to report it? Spec says items list contains the plan.
            # "plan(...) -> {items:[...], ...}"
            # Usually you list what you plan to do. If unavailable, do we list it?
            # "else 'unavailable' with a plain reason" implies it is an item in the list.
            # But which variant? The best compatible one? Or just the model?
            # Let's assume we list the best compatible variant as 'unavailable' or just the model.
            # The spec example: "CPU-only -> unavailable with reason".
            # I will list the best compatible variant if any, otherwise the first variant.
            rep_variant = compatible_variants[0] if compatible_variants else (variants[0] if variants else None)
            if rep_variant:
                items.append({
                    'goal': goal,
                    'model': model_id,
                    'variant': rep_variant.get('id', ''),
                    'mode': 'unavailable',
                    'reason': reason,
                    'est_vram_gb': rep_variant.get('peak_vram_gb', 0.0),
                    'download_gb': 0.0,
                    'comfy_flags': []
                })

    disk_ok = total_download_gb <= profile.get('disk_free_gb', 0.0)
    
    if not disk_ok:
        warnings.append(f"Insufficient disk space: need {total_download_gb:.2f} GB, have {profile.get('disk_free_gb', 0.0):.2f} GB")

    return {
        'items': items,
        'total_download_gb': total_download_gb,
        'disk_ok': disk_ok,
        'warnings': warnings
    }

def describe(profile):
    os_name = profile.get('os', 'unknown')
    gpus = profile.get('gpus', [])
    ram_gb = profile.get('ram_gb', 0.0)
    backend = profile.get('backend', 'cpu')
    
    gpu_str = ''
    if gpus:
        gpu = gpus[0]
        name = gpu.get('name', 'GPU')
        vram = gpu.get('vram_gb', 0.0)
        gpu_str = f", {name} ({vram:.0f} GB)"
        
    return f"{os_name.capitalize()}{gpu_str}, {ram_gb:.0f} GB RAM, {backend.upper()}"
