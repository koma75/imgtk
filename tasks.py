import os, glob
from pathlib import Path
from invoke import task

##############################################
### Setup default variables
##############################################

PY_VERSION = "3.11"
VENV_PY = Path(".venv/bin/python").resolve()

##############################################
### Helper Functions
##############################################

def run_rm(c, paths):
    """run rm -rf command equivalent for each pf against paths

    Args:
        c (Obj): invoke context object
        paths (List): List of paths to remove
    """
    # May not be necessary for *nix since rm command works on both files and directories,
    # But to keep consistency across platforms, use Python glob to expand all wildcards.
    files = []
    for f in paths:
        files.extend(glob.glob(f))

    # run file removal function based on platform
    if os.name == 'nt':
        for f in files:
            if os.isdir(f):
                c.run(f"rmdir /s /q {f}")
            else:
                c.run(f"del /s /f /q {f}")
    else:
        for f in files:
            c.run(f"rm -rf {f}")
    pass


##############################################
### Invoke Task Definitions
##############################################

@task()
def clean(c):
    """remove package artifacts"""
    run_rm(c, ["dist", "*.egg-info"])
    pass

@task()
def venv(c):
    """initialize a uv-managed dev venv"""
    c.run(f"uv venv --python {PY_VERSION} .venv")
    c.run("uv pip install build twine")

@task(pre=[clean])
def package(c):
    """Generate sdist"""
    c.run(f"{VENV_PY} -m build")

@task(pre=[package])
def publish(c):
    """upload to PyPi"""
    c.run(f"{VENV_PY} -m twine upload dist/*")

@task(pre=[package])
def pubtest(c):
    """upload to pypitest"""
    c.run(f"{VENV_PY} -m twine upload --repository pypitest dist/*")
    pass

@task(pre=[venv], default=True)
def build(c):
    """Build and install as editable"""
    c.run("uv pip install --editable .")
    pass

@task(pre=[build])
def test(c):
    """Run the CLI test harness (fixtures/outputs under testharness/)"""
    c.run("uv run runtests.py")
    pass
