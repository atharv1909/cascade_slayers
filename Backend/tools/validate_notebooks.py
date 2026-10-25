import nbformat, glob, os

nb_dir = r"D:\Cascade_slayers\training code"
for nb_path in sorted(glob.glob(os.path.join(nb_dir, "*.ipynb"))):
    name = os.path.basename(nb_path)
    nb = nbformat.read(nb_path, as_version=4)
    code_text = "\n".join([c.source for c in nb.cells if c.cell_type == "code"])
    # filter out ipython magic like !pip or %
    py_lines = []
    for line in code_text.splitlines():
        if line.strip().startswith("!") or line.strip().startswith("%"):
            py_lines.append("# " + line)
        else:
            py_lines.append(line)
    clean_code = "\n".join(py_lines)
    try:
        compile(clean_code, name, "exec")
        print(f"PASS: {name} (valid Python syntax)")
    except Exception as e:
        print(f"FAIL: {name} -> {e}")
