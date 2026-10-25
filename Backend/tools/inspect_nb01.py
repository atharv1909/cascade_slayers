import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\01_simulator_episode_generation.ipynb", as_version=4)
for idx, c in enumerate(nb.cells):
    if c.cell_type == "code":
        first_few = [l.strip() for l in c.source.splitlines() if l.strip() and not l.strip().startswith("#")][:2]
        header = " | ".join(first_few)
        print(f"Cell {idx:02d}: {header[:90]}")
