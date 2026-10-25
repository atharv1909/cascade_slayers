import nbformat

nb = nbformat.read(r"D:\Cascade_slayers\training code\01_simulator_episode_generation.ipynb", as_version=4)
print("=== Cell 4 Config ===")
print("\n".join(nb.cells[4].source.splitlines()[:30]))
print("=== Cell 27 Execution ===")
print("\n".join(nb.cells[27].source.splitlines()[:30]))
