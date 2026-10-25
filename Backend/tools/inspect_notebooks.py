import nbformat, os, glob, re

nb_dir = r"D:\Cascade_slayers\training code"
for nb_path in sorted(glob.glob(os.path.join(nb_dir, "*.ipynb"))):
    nb = nbformat.read(nb_path, as_version=4)
    print("=" * 60)
    print("FILE:", os.path.basename(nb_path))
    print("TOTAL CELLS:", len(nb.cells))
    data_lines = []
    for idx, c in enumerate(nb.cells):
        if c.cell_type == "code":
            for line in c.source.splitlines():
                line_lower = line.lower()
                if any(k in line_lower for k in ["kaggle", "read_csv", "read_parquet", "load_dataset", "calibrat", "usgs", "rain", "outage"]):
                    data_lines.append(f"  Line: {line.strip()[:100]}")
    print("Data-related lines:")
    for dl in data_lines[:12]:
        print(dl)
