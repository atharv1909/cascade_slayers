import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\02_chronos2_feature_extraction.ipynb", as_version=4)
print("=== Cell 5 Config ===")
print("\n".join(nb.cells[5].source.splitlines()[:35]))
