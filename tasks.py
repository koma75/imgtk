import os, glob
from pathlib import Path
from invoke import task

##############################################
### Setup default variables
##############################################

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

def cmd_updatepip():
    """return cli command to update pip inside venv if possible.

    Returns:
        String: cli command for updating pip inside venv
    """
    if os.name == 'nt':
        pfcmd = "echo Run 'pip install pip --upgrade' after activating venv using venv.bat"
    else:
        pfcmd = f"{VENV_PY} -m pip install pip --upgrade && {VENV_PY} -m pip install --upgrade build twine"
    return pfcmd


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
    """initialize venv"""
    c.run(f"{VENV_PY} -m venv .venv")
    c.run(cmd_updatepip())

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
    c.run(f"{VENV_PY} -m pip install --editable .")
    pass
