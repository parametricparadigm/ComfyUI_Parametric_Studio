import os
import tempfile
import shutil
import time
import glb

def test_cube_glb():
    data = glb.cube_glb()
    result = glb.inspect_glb(data)
    assert result["ok"], f"Expected ok, got problems: {result['problems']}"
    assert result["vertices"] == 24, f"Expected 24 vertices, got {result['vertices']}"
    assert result["triangles"] == 12, f"Expected 12 triangles, got {result['triangles']}"
    assert result["meshes"] == 1
    assert result["primitives"] == 1

def test_corrupt_magic():
    data = glb.cube_glb()
    corrupt = b'XXXX' + data[4:]
    result = glb.inspect_glb(corrupt)
    assert not result["ok"]
    assert any("magic" in p.lower() for p in result["problems"])

def test_truncated():
    data = glb.cube_glb()
    truncated = data[:10]
    result = glb.inspect_glb(truncated)
    assert not result["ok"]

def test_bad_length():
    data = glb.cube_glb()
    # Modify total length in header
    import struct
    header = data[:12]
    magic, version, length = struct.unpack('<4sII', header)
    bad_header = struct.pack('<4sII', magic, version, length + 10)
    bad_data = bad_header + data[12:]
    result = glb.inspect_glb(bad_data)
    assert not result["ok"]
    assert any("length" in p.lower() for p in result["problems"])

def test_list_glb():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some glb files
        file1 = os.path.join(tmpdir, "a.glb")
        file2 = os.path.join(tmpdir, "b.glb")
        file3 = os.path.join(tmpdir, "sub", "c.glb")
        
        os.makedirs(os.path.join(tmpdir, "sub"))
        
        with open(file1, 'wb') as f:
            f.write(glb.cube_glb())
        with open(file2, 'wb') as f:
            f.write(glb.cube_glb())
        with open(file3, 'wb') as f:
            f.write(glb.cube_glb())
            
        # Set different mtimes
        time.sleep(0.1)
        os.utime(file1, (time.time() - 100, time.time() - 100))
        time.sleep(0.1)
        os.utime(file2, (time.time() - 50, time.time() - 50))
        time.sleep(0.1)
        os.utime(file3, (time.time(), time.time()))
        
        # Create a symlink pointing outside
        outside_dir = tempfile.mkdtemp()
        outside_file = os.path.join(outside_dir, "outside.glb")
        with open(outside_file, 'wb') as f:
            f.write(glb.cube_glb())
            
        symlink = os.path.join(tmpdir, "link.glb")
        os.symlink(outside_file, symlink)
        
        # Create a symlinked directory
        outside_subdir = os.path.join(outside_dir, "subdir")
        os.makedirs(outside_subdir)
        outside_sub_file = os.path.join(outside_subdir, "sub.glb")
        with open(outside_sub_file, 'wb') as f:
            f.write(glb.cube_glb())
            
        symlink_dir = os.path.join(tmpdir, "linkdir")
        os.symlink(outside_subdir, symlink_dir)
        
        results = glb.list_glb(tmpdir)
        
        # Should have 3 files: a.glb, b.glb, sub/c.glb
        # Symlinks should be excluded
        assert len(results) == 3, f"Expected 3 files, got {len(results)}: {[r['path'] for r in results]}"
        
        # Check ordering: newest first
        # c.glb (newest), b.glb, a.glb (oldest)
        assert results[0]["path"] == "sub/c.glb"
        assert results[1]["path"] == "b.glb"
        assert results[2]["path"] == "a.glb"
        
        # Cleanup outside
        shutil.rmtree(outside_dir)

if __name__ == "__main__":
    test_cube_glb()
    test_corrupt_magic()
    test_truncated()
    test_bad_length()
    test_list_glb()
    print('ok')
