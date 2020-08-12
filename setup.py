import sys
from cx_Freeze import setup, Executable
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('Hue2_Linux.py', base=base)
]

setup(name='Hue2_Linux',
      version = '1.0',
      description = 'GUI controller for NZXT Hue2 RGB lights',
      author="Nathan Travers",
      author_email="NNathann@pm.me",
      options = {
          'build_exe': {
              'packages': ["gi"],
              'excludes': ["http", "urllib", "email", "xmlrpc", "_md5", "_sha1", "_sha3", "_sha256", "bz2", "lzma", "pickle", "unittest"],
              "include_files":["Hue2_Linux_GUI.glade"]
          }
      },
      executables = executables)
