import os
import gzip
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
runs_dir = os.path.join(ROOT, "runs")

compressed_count = 0
saved_bytes = 0

for root, dirs, files in os.walk(runs_dir):
    if "events.json" in files:
        src = os.path.join(root, "events.json")
        dst = os.path.join(root, "events.json.gz")
        orig_size = os.path.getsize(src)
        
        # Only compress if src > 0 bytes
        if orig_size > 0:
            with open(src, "rb") as f_in, gzip.open(dst, "wb", compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
            gz_size = os.path.getsize(dst)
            os.remove(src)
            saved_bytes += (orig_size - gz_size)
            compressed_count += 1
            print(f"Compressed {os.path.relpath(src, ROOT)}: {orig_size/(1024*1024):.1f}MB -> {gz_size/(1024*1024):.1f}MB")
        else:
            os.remove(src)

print(f"\nDone! Compressed {compressed_count} files, saved {saved_bytes/(1024*1024):.1f} MB.")
