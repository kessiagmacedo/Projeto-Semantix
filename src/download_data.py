"""Baixa a fonte pública e confere a integridade antes de salvar."""
from pathlib import Path
from urllib.request import urlopen
import hashlib

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv'
EXPECTED_MD5 = '470235f96568f28f9ea0da62234ec857'

def main():
    data = urlopen(URL, timeout=60).read()
    if hashlib.md5(data).hexdigest() != EXPECTED_MD5:
        raise ValueError('O arquivo da fonte mudou; revisar antes de usar.')
    target = ROOT/'data/DSL-StrongPasswordData.csv'
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(data)
    print('Base oficial salva e verificada:', target)

if __name__ == '__main__':
    main()
