# -*- mode: python -*-
import os
a = Analysis(['src/cli.py'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='potator.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True)
extra_files = [
    (os.path.join('ometa', 'parsley_termactions.parsley'),
     os.path.join('data', 'ometa', 'parsley_termactions.parsley'), 'DATA'),

    (os.path.join('ometa', 'parsley_tree_transformer.parsley'), os.path.join(
        'data', 'ometa', 'parsley_tree_transformer.parsley'), 'DATA'),

    (os.path.join('terml', 'quasiterm.parsley'),
     os.path.join('data', 'terml', 'quasiterm.parsley'), 'DATA'),

    (os.path.join('terml', 'terml.parsley'),
     os.path.join('data', 'terml', 'terml.parsley'), 'DATA'),
]
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               extra_files,
               strip=None,
               upx=True,
               name='potator')
