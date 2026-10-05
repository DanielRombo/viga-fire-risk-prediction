"""Auditoria final local: apenas leitura dos inputs e atualização do manifesto."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
EV = BASE / 'evidencias'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


manifesto = json.loads((EV / 'checksums_finais.json').read_text(encoding='utf-8'))
for nome, esperado in manifesto.items():
    assert sha(EV / nome) == esperado, nome
antes = (EV / 'producao_antes.txt').read_text(encoding='utf-8-sig').strip().splitlines()
depois = (EV / 'producao_depois.txt').read_text(encoding='utf-8-sig').strip().splitlines()
assert antes == depois
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
novos = subprocess.check_output(['git', 'ls-files', '-z', '--others', '--exclude-standard'], cwd=ROOT).decode('utf-8')
assert all(n.startswith('experiments/fwi_fase8/') for n in novos.split('\0') if n)
verificados = []
for p in BASE.iterdir():
    if p.suffix in ('.py', '.ps1', '.md'):
        texto = p.read_text(encoding='utf-8-sig')
        assert all(linha == linha.rstrip() for linha in texto.splitlines()), p.name
        if p.suffix == '.py':
            ast.parse(texto, filename=str(p))
        verificados.append(p.name)
resultado = dict(estado='aprovado', checksums_anteriores_verificados=len(manifesto),
    producao_metadados_iguais=True, ficheiros_rastreados_alterados=[],
    novos_apenas_fase8=True, git_diff_check=True, sintaxe_e_espacos=verificados,
    imagem_ensaio='sha256:01851c692dd3b127c8750229e44d002b2af089ae570c7dffde1782358ec2db81')
(EV / 'verificacao_final.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
ficheiros = {str(p.relative_to(EV)): sha(p) for p in sorted(EV.rglob('*'))
             if p.is_file() and p.name != 'checksums_finais.json'}
(EV / 'checksums_finais.json').write_text(json.dumps(ficheiros, ensure_ascii=False, indent=2), encoding='utf-8')
print('Auditoria final aprovada: checksums, produção, âmbito, sintaxe e git diff --check.')
