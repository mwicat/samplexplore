import os
import pathlib
import subprocess
import sys


def open_file(path: pathlib.Path):
    os.startfile(str(path), 'open')


def open_file_parent(path: pathlib.Path):
    if sys.platform == 'win32':
        subprocess.Popen(f'explorer /select,{path}')
    else:
        os.startfile(str(path), 'open')
