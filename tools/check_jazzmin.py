import sys, os, importlib, pkgutil, traceback
print('sys.executable:', sys.executable)
print('\n-- sys.path --')
for p in sys.path:
    print(' ', p)
print('\n-- find_spec(jazzmin) --')
print(importlib.util.find_spec('jazzmin'))
print('\n-- pkgutil.iter_modules has jazzmin? --')
print(any(m.name=='jazzmin' for m in pkgutil.iter_modules()))
print('\n-- try import jazzmin --')
try:
    import jazzmin
    print('import OK ->', getattr(jazzmin, '__file__', None))
except Exception:
    print('import FAILED')
    traceback.print_exc()

sp = os.path.normpath(os.path.join(os.path.dirname(sys.executable), '..', 'Lib', 'site-packages'))
print('\nsite-packages detected:', sp)
if os.path.isdir(sp):
    print('\n-- jazz* entries in site-packages --')
    for f in sorted([f for f in os.listdir(sp) if 'jazz' in f.lower()]):
        print('  ', f)
else:
    print('site-packages dir not found')
