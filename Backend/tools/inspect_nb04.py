import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\04_lgbm_risk_calibration.ipynb", as_version=4)
for idx in [3, 8, 10, 15]:
    c = nb.cells[idx]
    print(f"--- Cell {idx} ---")
    for line in c.source.splitlines()[:15]:
        print(" ", line)
