"""Minimal OSC 1.0 over UDP (original, stdlib): send and receive messages with int/float/string/bool arguments. Defaults to localhost only (TouchDesigner, Max, Unreal, Resolume, VCV...)."""
import socket, struct

class OSCError(ValueError): pass
def _pad(b): return b + b"\x00" * (4 - len(b) % 4)

def encode(address, args=()):
    if not address.startswith("/") or len(address) > 256: raise OSCError("bad OSC address")
    tags, data = ",", b""
    for a in args:
        if isinstance(a, bool): tags += "T" if a else "F"
        elif isinstance(a, int): tags += "i"; data += struct.pack(">i", a)
        elif isinstance(a, float): tags += "f"; data += struct.pack(">f", a)
        elif isinstance(a, str): tags += "s"; data += _pad(a.encode()[:1024] + b"\x00")[: len(_pad(a.encode()[:1024] + b"\x00"))]
        else: raise OSCError("unsupported argument type")
    return _pad(address.encode() + b"\x00") + _pad(tags.encode() + b"\x00") + data

def _read_str(b, i):
    j = b.index(b"\x00", i); s = b[i:j].decode("utf-8", "replace"); return s, (j + 4) & ~3

def decode(packet):
    try:
        addr, i = _read_str(packet, 0); tags, i = _read_str(packet, i); args = []
        for t in tags[1:]:
            if t == "i": args.append(struct.unpack(">i", packet[i:i + 4])[0]); i += 4
            elif t == "f": args.append(struct.unpack(">f", packet[i:i + 4])[0]); i += 4
            elif t == "s": s, i = _read_str(packet, i); args.append(s)
            elif t == "T": args.append(True)
            elif t == "F": args.append(False)
            else: raise OSCError(f"unsupported type tag {t}")
        return addr, args
    except (ValueError, struct.error, IndexError) as e: raise OSCError(f"malformed OSC packet: {e}")

def send(host, port, address, args=(), allowed_hosts=("127.0.0.1", "localhost", "::1")):
    if host not in allowed_hosts: raise OSCError("host is not allowed")
    with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_DGRAM) as s: s.sendto(encode(address, args), (host, int(port)))

def receive(port, timeout=5.0, host="127.0.0.1", max_size=4096):
    """-> (address, args) or None on timeout. Binds to localhost by default."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind((host, int(port)))
        try: data, _ = s.recvfrom(max_size)
        except socket.timeout: return None
    return decode(data)
