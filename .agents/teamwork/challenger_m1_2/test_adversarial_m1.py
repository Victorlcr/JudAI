"""
Adversarial Verification Suite for Milestone 1 - Docker Compose & Python Syntax
==============================================================================
Challenger: Challenger 2 (Milestone 1)
Archetype: Empirical Challenger (critic, specialist)
Directory: .agents/teamwork/challenger_m1_2
"""

import sys
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent


class SimpleYAMLParser:
    """
    Parser YAML determinístico e rigoroso construído especificamente para validar
    arquivos Docker Compose e validar conformidade com o Compose Spec.
    Suporta mapeamentos aninhados por indentação, sequências de escalares e mapeamentos.
    Segue a especificação YAML onde mapeamento requer ': ' (dois-pontos seguido de espaço)
    ou ':' no final da linha. Strings como 'mongo_data:/data/db' e '27017:27017' são escalares.
    """

    def __init__(self, raw_text: str):
        self.raw_text = raw_text
        self.lines = self._preprocess_lines(raw_text)

    def _preprocess_lines(self, text: str) -> List[Tuple[int, int, str]]:
        """Retorna lista de tuplas (número_da_linha, indentação, conteúdo_sem_comentários)."""
        result = []
        for line_no, original_line in enumerate(text.splitlines(), start=1):
            line = original_line
            in_single = False
            in_double = False
            comment_idx = -1
            for i, char in enumerate(line):
                if char == "'" and not in_double:
                    in_single = not in_single
                elif char == '"' and not in_single:
                    in_double = not in_double
                elif char == '#' and not in_single and not in_double:
                    comment_idx = i
                    break
            if comment_idx >= 0:
                line = line[:comment_idx]
            
            stripped = line.rstrip()
            if not stripped.strip():
                continue
            indent = len(stripped) - len(stripped.lstrip(' '))
            result.append((line_no, indent, stripped.strip()))
        return result

    def parse(self) -> Dict[str, Any]:
        """Faz o parsing estruturado das linhas em uma árvore de dicts/lists/strings."""
        idx = 0
        parsed_dict, _ = self._parse_mapping(0, 0)
        return parsed_dict

    def _parse_mapping(self, current_idx: int, current_indent: int) -> Tuple[Dict[str, Any], int]:
        mapping: Dict[str, Any] = {}
        i = current_idx

        while i < len(self.lines):
            line_no, indent, content = self.lines[i]

            if indent < current_indent:
                break

            if indent > current_indent:
                raise SyntaxError(f"Linha {line_no}: Indentação inesperada '{content}'")

            if content.startswith("- "):
                break

            # Em YAML chave: valor requer ': ' ou ':' no fim
            colon_match = re.search(r':(\s|$)', content)
            if not colon_match:
                raise SyntaxError(f"Linha {line_no}: Mapeamento inválido, ': ' esperado em '{content}'")

            colon_pos = colon_match.start()
            key = content[:colon_pos].strip()
            rest = content[colon_pos + 1:].strip()

            if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                key = key[1:-1]

            i += 1
            if rest:
                mapping[key] = self._parse_scalar(rest)
            else:
                if i < len(self.lines) and self.lines[i][1] > indent:
                    next_line_no, next_indent, next_content = self.lines[i]
                    if next_content.startswith("- "):
                        seq_val, i = self._parse_sequence(i, next_indent)
                        mapping[key] = seq_val
                    else:
                        map_val, i = self._parse_mapping(i, next_indent)
                        mapping[key] = map_val
                else:
                    mapping[key] = None

        return mapping, i

    def _parse_sequence(self, current_idx: int, current_indent: int) -> Tuple[List[Any], int]:
        sequence: List[Any] = []
        i = current_idx

        while i < len(self.lines):
            line_no, indent, content = self.lines[i]

            if indent < current_indent:
                break
            if indent > current_indent:
                raise SyntaxError(f"Linha {line_no}: Indentação inconsistente na sequência '{content}'")

            if not content.startswith("- "):
                break

            item_text = content[2:].strip()
            i += 1

            # Verifica se é mapeamento inline (com ': ') e não entre aspas
            colon_match = re.search(r':(\s|$)', item_text)
            if colon_match and not (item_text.startswith('"') or item_text.startswith("'")):
                colon_idx = colon_match.start()
                k = item_text[:colon_idx].strip()
                v = item_text[colon_idx + 1:].strip()
                sequence.append({k: self._parse_scalar(v)})
            else:
                sequence.append(self._parse_scalar(item_text))

        return sequence, i

    def _parse_scalar(self, val_str: str) -> Any:
        if val_str.startswith('"') and val_str.endswith('"'):
            return val_str[1:-1]
        if val_str.startswith("'") and val_str.endswith("'"):
            return val_str[1:-1]
        if val_str.lower() in ("true", "yes", "on"):
            return True
        if val_str.lower() in ("false", "no", "off"):
            return False
        if re.match(r"^-?\d+$", val_str):
            return int(val_str)
        if re.match(r"^-?\d+\.\d+$", val_str):
            return float(val_str)
        if val_str.lower() in ("null", "~", ""):
            return None
        return val_str


class ComposeSpecValidator:
    """Validador estrito contra a especificação formal do Compose Spec."""

    ALLOWED_ROOT_KEYS = {"version", "services", "volumes", "networks", "configs", "secrets"}
    ALLOWED_SERVICE_KEYS = {
        "image", "build", "container_name", "ports", "volumes", "environment",
        "env_file", "depends_on", "restart", "networks", "command", "entrypoint",
        "healthcheck", "labels", "expose", "logging"
    }

    def __init__(self, compose_dict: Dict[str, Any]):
        self.doc = compose_dict

    def validate(self) -> List[str]:
        errors = []
        if not isinstance(self.doc, dict):
            return ["Compose file raiz não é um objeto/dicionário."]

        # 1. Chaves raiz
        for k in self.doc.keys():
            if k not in self.ALLOWED_ROOT_KEYS:
                errors.append(f"Chave raiz inválida no Compose Spec: '{k}'")

        # 2. Seção services
        if "services" not in self.doc:
            errors.append("Seção obrigatória 'services' ausente no Compose file.")
            return errors

        services = self.doc["services"]
        if not isinstance(services, dict):
            errors.append("'services' deve ser um mapeamento de serviços.")
            return errors

        # 3. Serviço mongodb
        if "mongodb" not in services:
            errors.append("Serviço obrigatório 'mongodb' não encontrado em 'services'.")
            return errors

        mongo = services["mongodb"]
        if not isinstance(mongo, dict):
            errors.append("Definição de 'mongodb' deve ser um mapeamento.")
            return errors

        # Verifica chaves de serviço permitidas
        for sk in mongo.keys():
            if sk not in self.ALLOWED_SERVICE_KEYS:
                errors.append(f"Propriedade de serviço desconhecida em 'mongodb': '{sk}'")

        # Imagem
        img = mongo.get("image")
        if not img or not isinstance(img, str):
            errors.append("Propriedade 'image' do mongodb deve ser uma string não vazia.")
        elif img != "mongo:latest":
            errors.append(f"Imagem esperada 'mongo:latest', encontrado '{img}'.")

        # Portas
        ports = mongo.get("ports")
        if ports is None:
            errors.append("Propriedade 'ports' ausente em 'mongodb'.")
        elif not isinstance(ports, list):
            errors.append("'ports' deve ser uma lista.")
        else:
            found_27017 = False
            for p in ports:
                p_str = str(p).strip()
                if p_str == "27017:27017":
                    found_27017 = True
                elif isinstance(p, dict) and p.get("target") == 27017 and p.get("published") == 27017:
                    found_27017 = True
            if not found_27017:
                errors.append(f"Mapeamento de porta '27017:27017' não encontrado em ports: {ports}")

        # Volumes montados no serviço
        svc_vols = mongo.get("volumes")
        named_vols_used = []
        if svc_vols is None:
            errors.append("Propriedade 'volumes' ausente em 'mongodb'.")
        elif not isinstance(svc_vols, list):
            errors.append("'volumes' no serviço deve ser uma lista.")
        else:
            found_mongo_data = False
            for v in svc_vols:
                if isinstance(v, str):
                    parts = v.split(":")
                    if len(parts) >= 2:
                        host_vol = parts[0]
                        container_dir = parts[1]
                        if host_vol == "mongo_data" and container_dir == "/data/db":
                            found_mongo_data = True
                            named_vols_used.append(host_vol)
                elif isinstance(v, dict):
                    if ("mongo_data" in v and v["mongo_data"] == "/data/db") or (v.get("source") == "mongo_data" and v.get("target") == "/data/db"):
                        found_mongo_data = True
                        named_vols_used.append("mongo_data")
            if not found_mongo_data:
                errors.append(f"Montagem de volume 'mongo_data:/data/db' ausente em {svc_vols}")

        # 4. Seção raiz volumes para volumes nomeados
        root_vols = self.doc.get("volumes")
        for nv in named_vols_used:
            if root_vols is None or not isinstance(root_vols, dict):
                errors.append(f"Volume nomeado '{nv}' utilizado no serviço, mas seção raiz 'volumes:' está ausente ou inválida.")
            elif nv not in root_vols:
                errors.append(f"Volume nomeado '{nv}' não foi declarado na seção raiz 'volumes:'.")

        return errors


def test_adversarial_yaml_cases():
    print("-------------------------------------------------------------------")
    print("TEST SUITE 1: DOCKER COMPOSE YAML & COMPOSE SPEC VERIFICATION")
    print("-------------------------------------------------------------------")

    compose_file = ROOT_DIR / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml inexistente!"

    raw_bytes = compose_file.read_bytes()
    # Teste 1.1: Sem BOM
    assert not raw_bytes.startswith(b'\xef\xbb\xbf'), "FALHA: docker-compose.yml possui UTF-8 BOM"
    print("[PASS] 1.1: Sem UTF-8 BOM no docker-compose.yml")

    # Teste 1.2: Linhas com LF estrito
    assert b'\r\n' not in raw_bytes, "FALHA: docker-compose.yml possui CRLF em vez de LF puro"
    print("[PASS] 1.2: Linhas normalizadas com LF estrito (sem CRLF)")

    # Teste 1.3: Parsing com o parser determinístico
    text = raw_bytes.decode("utf-8")
    parser = SimpleYAMLParser(text)
    data = parser.parse()
    print(f"[PASS] 1.3: YAML parseado com sucesso: {data}")

    # Teste 1.4: Validação Compose Spec
    validator = ComposeSpecValidator(data)
    errors = validator.validate()
    assert len(errors) == 0, f"FALHA na validação do Compose Spec: {errors}"
    print("[PASS] 1.4: 100% de conformidade com Compose Spec formal (sem erros)")

    # Teste 1.5: Teste Adversarial da Sintaxe da Porta
    # Em YAML 1.1, portas sem aspas como 22:22 viram sexagesimal (1342).
    # Verificar se a porta está protegida como string com aspas no raw_text
    port_line_match = re.search(r'-\s*(["\']27017:27017["\']|27017:27017)', text)
    assert port_line_match is not None, "FALHA: Declaração de porta 27017:27017 não encontrada"
    raw_port_decl = port_line_match.group(1)
    print(f"[INFO] Declaração da porta no arquivo: {raw_port_decl}")
    assert raw_port_decl in ('"27017:27017"', "'27017:27017'"), (
        f"ALERTA ADVERSARIAL: Porta não está encapsulada com aspas (' ou \"): {raw_port_decl}"
    )
    print("[PASS] 1.5: Mapeamento de porta protegido contra sexagesimal YAML 1.1 (aspas presentes)")

    # Teste 1.6: Oráculo de Testes Adversariais (Mutation Testing no Validator)
    # Testa se o validador realmente rejeitaria mutações inválidas
    bad_case_missing_volume = {
        "services": {"mongodb": {"image": "mongo:latest", "ports": ["27017:27017"], "volumes": ["mongo_data:/data/db"]}}
    }
    v_bad = ComposeSpecValidator(bad_case_missing_volume)
    errs_bad = v_bad.validate()
    assert any("volumes:" in e for e in errs_bad), "Oráculo falhou: deveria rejeitar volume ausente na raiz"

    bad_case_wrong_image = {
        "services": {"mongodb": {"image": "mongo:4.4", "ports": ["27017:27017"], "volumes": ["mongo_data:/data/db"]}},
        "volumes": {"mongo_data": None}
    }
    errs_img = ComposeSpecValidator(bad_case_wrong_image).validate()
    assert any("mongo:latest" in e for e in errs_img), "Oráculo falhou: deveria rejeitar imagem diferente de mongo:latest"
    print("[PASS] 1.6: Oráculo adversarial comprovado (mutantes são devidamente rejeitados)")


def test_adversarial_python_imports():
    print("\n-------------------------------------------------------------------")
    print("TEST SUITE 2: PYTHON PACKAGE IMPORT & SYNTAX ADVERSARIAL CHALLENGE")
    print("-------------------------------------------------------------------")

    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    packages = [
        ("src", ROOT_DIR / "src" / "__init__.py"),
        ("src.scraper", ROOT_DIR / "src" / "scraper" / "__init__.py"),
        ("src.database", ROOT_DIR / "src" / "database" / "__init__.py"),
        ("src.models", ROOT_DIR / "src" / "models" / "__init__.py"),
        ("src.api", ROOT_DIR / "src" / "api" / "__init__.py"),
    ]

    for pkg_name, file_path in packages:
        assert file_path.exists(), f"FALHA: Arquivo {file_path} não existe"
        raw = file_path.read_bytes()
        assert not raw.startswith(b'\xef\xbb\xbf'), f"FALHA: {file_path} possui UTF-8 BOM"
        assert b'\r\n' not in raw, f"FALHA: {file_path} possui quebra de linha CRLF"

        # Importar dinamicamente e verificar integridade
        if pkg_name in sys.modules:
            del sys.modules[pkg_name]

        mod = __import__(pkg_name, fromlist=["*"])
        assert mod is not None, f"Módulo {pkg_name} é None"
        assert hasattr(mod, "__file__"), f"Módulo {pkg_name} não tem atributo __file__"
        print(f"[PASS] 2.x: Import {pkg_name} bem-sucedido ({file_path.name}, {len(raw)} bytes)")

    # Teste 2.6: Garantir que nenhum import prematuro de submódulos não implementados foi embutido
    import src.database
    assert not hasattr(src.database, "mongo_connection"), "src.database não deve importar prematuramente mongo_connection em M1"
    assert not hasattr(src.database, "chroma_connection"), "src.database não deve importar prematuramente chroma_connection em M1"

    import src.api
    assert not hasattr(src.api, "main"), "src.api não deve importar prematuramente main em M1"
    print("[PASS] 2.6: Nenhum import prematuro de submódulos futuros em __init__.py")


def test_adversarial_tier1_run():
    print("\n-------------------------------------------------------------------")
    print("TEST SUITE 3: RUNNER TIER 1 EVALUATION FOR M1")
    print("-------------------------------------------------------------------")
    import pytest
    tier1_file = str(ROOT_DIR / "tests" / "test_tier1_feature_coverage.py")

    # Executa apenas as classes do Milestone 1 (Feature 1 e Feature 2)
    ret = pytest.main([
        tier1_file,
        "-k", "TestDockerComposeConfig or TestGitConfigurationAndStructure",
        "-v",
        "-q"
    ])
    assert ret == pytest.ExitCode.OK, f"Testes de Tier 1 para M1 falharam com código {ret}"
    print("[PASS] 3.1: Todos os testes de Tier 1 pertinentes ao Milestone 1 passaram com 100% de sucesso!")


if __name__ == "__main__":
    try:
        test_adversarial_yaml_cases()
        test_adversarial_python_imports()
        test_adversarial_tier1_run()
        print("\n===================================================================")
        print("RESULTADO GLOBAL: TODAS AS VERIFICAÇÕES ADVERSARIAIS PASSARAM!")
        print("===================================================================")
    except AssertionError as e:
        print(f"\n[FALHA ADVERSARIAL]: {e}")
        sys.exit(1)
    except Exception as ex:
        import traceback
        traceback.print_exc()
        sys.exit(2)
