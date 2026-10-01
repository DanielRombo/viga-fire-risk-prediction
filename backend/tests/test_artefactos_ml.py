"""Validação do conjunto real e falhas em cópias descartáveis."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import artefactos_ml as artefactos


class ArtefactosMLTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / 'backend'
        shutil.copytree(Path(artefactos.__file__).parent, self.pasta / 'services', ignore=shutil.ignore_patterns('__pycache__'))
        modelos = self.pasta / 'ml_models'
        modelos.mkdir()
        for nome in (*artefactos.NOMES, 'manifesto.json'):
            shutil.copy2(artefactos.PASTA_MODELOS / nome, modelos / nome)
        self.modelos = modelos

    def executar(self, *args):
        return subprocess.run([sys.executable, '-B', *args], cwd=self.pasta,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')

    def test_conjunto_real_e_copia_limpa(self):
        self.assertEqual(len(artefactos.carregar_artefactos()), 5)
        for args in [('-m', 'services.artefactos_ml'),
                     ('-c', 'from datetime import datetime; from services.modelo_ml import prever_risco; r = prever_risco({"distrito":"Lisboa","latitude":38.7,"longitude":-9.1,"data_hora":datetime(2024,7,1,12)}); assert r["estado"] == "parcial" and r["probabilidade_incendio"] is not None')]:
            resultado = self.executar(*args)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_cada_ausencia_bloqueia_validacao_e_arranque(self):
        for nome in artefactos.NOMES:
            with self.subTest(nome=nome):
                ficheiro = self.modelos / nome
                conteudo = ficheiro.read_bytes()
                ficheiro.unlink()
                for args in [('-m', 'services.artefactos_ml'), ('-c', 'import services.modelo_ml')]:
                    resultado = self.executar(*args)
                    self.assertNotEqual(resultado.returncode, 0)
                    self.assertIn(nome, resultado.stderr)
                ficheiro.write_bytes(conteudo)

    def test_corrupcao_bloqueia_antes_de_desserializar(self):
        (self.modelos / artefactos.NOMES[0]).write_bytes(b'invalido')
        with patch.object(artefactos.joblib, 'load') as carregar:
            with self.assertRaisesRegex(RuntimeError, 'Checksum ML'):
                artefactos.carregar_artefactos(self.modelos)
            carregar.assert_not_called()
        for args in [('-m', 'services.artefactos_ml'), ('-c', 'import services.modelo_ml')]:
            self.assertNotEqual(self.executar(*args).returncode, 0)

    def test_scaler_trocado_mesmo_com_hash_atualizado(self):
        shutil.copy2(self.modelos / 'scaler_anpc.joblib', self.modelos / 'scaler_kaggle.joblib')
        manifesto = json.loads((self.modelos / 'manifesto.json').read_text())
        manifesto['sha256']['scaler_kaggle.joblib'] = hashlib.sha256((self.modelos / 'scaler_kaggle.joblib').read_bytes()).hexdigest()
        (self.modelos / 'manifesto.json').write_text(json.dumps(manifesto))
        resultado = self.executar('-m', 'services.artefactos_ml')
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn('incompat', resultado.stderr)

    def test_instalacao_explicita_do_conjunto_aprovado(self):
        (self.modelos / artefactos.NOMES[0]).unlink()
        resultado = self.executar('-m', 'services.artefactos_ml', '--origem', str(artefactos.PASTA_MODELOS))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(len(list(self.modelos.glob('*.joblib'))), 5)
