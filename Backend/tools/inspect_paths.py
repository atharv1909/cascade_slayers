import nbformat, glob, os

nb_dir = r"D:\Cascade_slayers\training code"
for nb_path in sorted(glob.glob(os.path.join(nb_dir, "*.ipynb"))):
    name = os.path.basename(nb_path)
    nb = nbformat.read(nb_path, as_version=4)
    print("=" * 60)
    print("NOTEBOOK:", name)
    for idx, c in enumerate(nb.cells):
        if c.cell_type == "code":
            src = c.source
            if "class " in src and ("Config" in src or "Path" in src):
                print(f"--- Cell {idx} Config ---")
                for line in src.splitlines():
                    if any(k in line for k in ["DIR", "PATH", "INPUT", "OUTPUT", "Path("]):
                        print(" ", line.strip())
