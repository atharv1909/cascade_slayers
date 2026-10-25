import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\05_etas_seismic_model.ipynb", as_version=4)
for idx, c in enumerate(nb.cells):
    if c.cell_type == "code" and any(k in c.source.lower() for k in ["usgs", "read_csv", "catalog", "load_data"]):
        print(f"--- Cell {idx} ---")
        for line in c.source.splitlines()[:15]:
            print(" ", line)
