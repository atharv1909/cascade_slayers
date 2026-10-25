import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\01_simulator_episode_generation.ipynb", as_version=4)
for idx in range(9, 19):
    c = nb.cells[idx]
    src = c.source
    lines = [l for l in src.splitlines() if "calibrat" in l.lower() or "real" in l.lower() or "distribution" in l.lower() or "dataset" in l.lower()]
    print(f"Cell {idx} ({c.source.splitlines()[0][:35]}): {len(lines)} calibration references")
    for l in lines[:3]:
        print("  ", l.strip()[:90])
