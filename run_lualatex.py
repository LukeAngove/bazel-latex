#!/usr/bin/env python3

import glob
import os
import shutil
import subprocess
import sys

# Walk through all externals. If they start with the special prefix
# texlive_{extra,texmf}__ prefix, it means they should be part of the
# texmf directory. LaTeX utilities don't seem to like the use of
# symlinks, so move the externals into the texmf directory.
#
# Externals that do not start with the special prefix should be added to
# TEXINPUTS, so that inclusions of external resources works.
texinputs = [""] + glob.glob("bazel-out/*/bin")
for external in sorted(os.listdir("external")):
    src = os.path.abspath(os.path.join("external", external))
    if external.startswith("texlive_extra__") or external.startswith("texlive_texmf__"):
        dst = os.path.join("texmf", "/".join(external.split("__")[1:]))
        try:
            os.makedirs(os.path.dirname(dst))
        except OSError:
            pass
        os.rename(src, dst)
    else:
        texinputs.append(src)

(
    kpsewhich_file,
    luatex_file,
    latexrun_file,
    job_name,
    main_file,
    output_file,
) = sys.argv[1:]

env = dict(os.environ)
env["OPENTYPEFONTS"] = ":".join(texinputs)
env["PATH"] = "%s:%s" % (os.path.abspath("bin"), env["PATH"])
env["SOURCE_DATE_EPOCH"] = "0"
env["TEXINPUTS"] = ":".join(texinputs)
env["TEXMF"] = os.path.abspath("texmf/texmf-dist")
env["TEXMFCNF"] = os.path.abspath("texmf/texmf-dist/web2c")
env["TEXMFROOT"] = os.path.abspath("texmf")
env["TTFONTS"] = ":".join(texinputs)

os.mkdir("bin")
shutil.copy(kpsewhich_file, "bin/kpsewhich")
shutil.copy(luatex_file, "bin/lualatex")
os.link("bin/lualatex", "bin/luatex")
shutil.copy("texmf/texmf-dist/scripts/texlive/fmtutil.pl", "bin/mktexfmt")

# Find all directories in included files.
import re
with open(main_file) as m:
    dirs = set(re.findall("\s*\\\include\{([^}]*)/[^}]+\}", m.read()))

# Create all directories. If they already exist, don't worry.
# This is needed if building files from other directories than the one
# with the current BUILD.bazel
import pathlib
for d in dirs:
    D = pathlib.Path(d)
    D.mkdir(exist_ok=True)

return_code = subprocess.call(
    args=[
        latexrun_file,
        "--latex-args=-jobname=" + job_name,
        "--latex-cmd=lualatex",
        "-Wall",
        main_file,
    ],
    env=env,
)
if return_code != 0:
    sys.exit(return_code)
os.rename(job_name + ".pdf", output_file)
