import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\05_etas_seismic_model.ipynb", as_version=4)
c5 = nb.cells[5].source
print("\n".join(c5.splitlines()[:45]))
