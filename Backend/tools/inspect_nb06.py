import nbformat, glob, os

nb = nbformat.read(r"D:\Cascade_slayers\training code\06_full_evaluation_scoring.ipynb", as_version=4)
for idx, c in enumerate(nb.cells):
    if c.cell_type == "code" and "KAGGLE" in c.source:
        print(f"--- Cell {idx} ---")
        for line in c.source.splitlines():
            if any(k in line for k in ["BASE", "INPUT", "WORKING", "Path("]):
                print(" ", line.strip())
