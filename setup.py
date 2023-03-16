import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "zip_include_packages": ["encodings", "PySide2"],
    "include_msvcr": True,
}

# base="Win32GUI" should be used only for Windows GUI app
base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="samplexplore",
    version="0.9.0",
    description="",
    options={"build_exe": build_exe_options},
    executables=[Executable(
        "scripts/samplexplore.py",
        target_name="Samplexplore",
        icon="resources/icon.ico",
        base=base)],
)
