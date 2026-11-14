"""
Testes Adversariais e de Integração Frontend-Backend (Milestone 4)
==================================================================
Challenger: challenger_m4_2
Alvo: Interface Web integrada servida em GET / (src/api/templates/index.html)
      e Contrato de Integração JavaScript <-> API FastAPI (src/api/main.py)

Dimensões de Teste:
1. Integridade Estrutural do HTML via BeautifulSoup e lxml.
2. Presença e atributos das 3 Visões (Moderno, Clássico e Comparação).
3. Conformidade e listeners dos 5 Chips de Perguntas de Exemplo.
4. Análise Estática e Validação de Sintaxe do JavaScript via Node.js runtime.
5. Contrato de Integração API <-> JS (rotas fetch, payloads e schemas consumidos).
6. Resiliência Offline e Autonomia (ausência de CDNs, fontes remotas ou scripts externos).
7. Segurança e Higienização XSS (função escapeHtml e injeções seguras).
8. Integração ponta-a-ponta via TestClient(app) no endpoint GET /.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup
import lxml.html
from fastapi.testclient import TestClient

# Adiciona a raiz do projeto ao sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.main import (
    app,
    QueryRequest,
    ClassicArticleResult,
    BertArticleResult,
    SearchTfidfResponse,
    SearchBertResponse,
    CompareResponse,
    ModelStatusResponse,
)


class TestFrontendIntegrationChallenger(unittest.TestCase):
    """Suíte adversarial de desafio à integração frontend-backend e templates."""

    TEMPLATE_PATH = PROJECT_ROOT / "src" / "api" / "templates" / "index.html"

    @classmethod
    def setUpClass(cls):
        """Carrega o conteúdo do template HTML e inicializa o TestClient."""
        if not cls.TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Arquivo de template ausente em: {cls.TEMPLATE_PATH}")

        with open(cls.TEMPLATE_PATH, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

        # Parsers
        cls.soup = BeautifulSoup(cls.html_content, "html.parser")
        cls.lxml_tree = lxml.html.fromstring(cls.html_content)

        # TestClient para chamadas ao vivo
        cls.client = TestClient(app)

    # =========================================================================
    # 1. INTEGRIDADE ESTRUTURAL DO HTML
    # =========================================================================

    def test_01_html_parser_integrity_bs4_and_lxml(self):
        """Verifica se o HTML é perfeitamente parseável por bs4 e lxml sem erros."""
        # 1. bs4 com html.parser
        soup_html = BeautifulSoup(self.html_content, "html.parser")
        self.assertIsNotNone(soup_html.find("html"))
        self.assertIsNotNone(soup_html.find("head"))
        self.assertIsNotNone(soup_html.find("body"))

        # 2. bs4 com lxml parser
        soup_lxml = BeautifulSoup(self.html_content, "lxml")
        self.assertIsNotNone(soup_lxml.find("html"))

        # 3. lxml nativo
        tree = lxml.html.fromstring(self.html_content)
        self.assertEqual(tree.tag, "html")

        # 4. Doctype e charset
        self.assertTrue(self.html_content.lstrip().startswith("<!DOCTYPE html>"))
        meta_charset = soup_html.find("meta", charset=True)
        self.assertIsNotNone(meta_charset)
        self.assertEqual(meta_charset["charset"].lower(), "utf-8")

        # 5. Meta viewport para responsividade
        meta_viewport = soup_html.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(meta_viewport)
        self.assertIn("width=device-width", meta_viewport["content"])

    # =========================================================================
    # 2. VERIFICAÇÃO DAS 3 VISÕES (NAVEGAÇÃO, ABAS E PAINÉIS)
    # =========================================================================

    def test_02_navigation_tabs_and_views_structure(self):
        """Verifica a presença dos seletores, botões e painéis para as 3 visões."""
        # Barra de navegação
        nav_tabs = self.soup.find("nav", class_="tabs-nav")
        self.assertIsNotNone(nav_tabs, "Elemento <nav class='tabs-nav'> ausente.")
        self.assertEqual(nav_tabs.get("role"), "tablist")

        # 3 Botões de navegação
        btn_compare = self.soup.find("button", id="tab-btn-compare")
        btn_modern = self.soup.find("button", id="tab-btn-modern")
        btn_classic = self.soup.find("button", id="tab-btn-classic")

        self.assertIsNotNone(btn_compare, "Botão #tab-btn-compare ausente.")
        self.assertIsNotNone(btn_modern, "Botão #tab-btn-modern ausente.")
        self.assertIsNotNone(btn_classic, "Botão #tab-btn-classic ausente.")

        # Atributos ARIA e chamadas onclick
        self.assertEqual(btn_compare.get("role"), "tab")
        self.assertEqual(btn_modern.get("role"), "tab")
        self.assertEqual(btn_classic.get("role"), "tab")

        self.assertIn("switchTab('compare')", btn_compare.get("onclick", ""))
        self.assertIn("switchTab('modern')", btn_modern.get("onclick", ""))
        self.assertIn("switchTab('classic')", btn_classic.get("onclick", ""))

        # Visão default ativa: compare
        self.assertEqual(btn_compare.get("aria-selected"), "true")
        self.assertIn("active", btn_compare.get("class", []))

        # 3 Painéis correspondentes
        pane_compare = self.soup.find("div", id="pane-compare")
        pane_modern = self.soup.find("div", id="pane-modern")
        pane_classic = self.soup.find("div", id="pane-classic")

        self.assertIsNotNone(pane_compare, "Painel #pane-compare ausente.")
        self.assertIsNotNone(pane_modern, "Painel #pane-modern ausente.")
        self.assertIsNotNone(pane_classic, "Painel #pane-classic ausente.")

        self.assertEqual(pane_compare.get("role"), "tabpanel")
        self.assertEqual(pane_modern.get("role"), "tabpanel")
        self.assertEqual(pane_classic.get("role"), "tabpanel")

        self.assertIn("tab-pane", pane_compare.get("class", []))
        self.assertIn("tab-pane", pane_modern.get("class", []))
        self.assertIn("tab-pane", pane_classic.get("class", []))

        # Painel compare deve estar ativo inicialmente
        self.assertIn("active", pane_compare.get("class", []))
        self.assertNotIn("active", pane_modern.get("class", []))
        self.assertNotIn("active", pane_classic.get("class", []))

    def test_03_results_containers_in_all_views(self):
        """Verifica a existência dos containers de resultados específicos de cada visão."""
        # 1. Visão Comparação
        self.assertIsNotNone(self.soup.find("div", id="compare-results"))
        self.assertIsNotNone(self.soup.find("span", id="summary-agreement"))
        self.assertIsNotNone(self.soup.find("span", id="summary-latency-classic"))
        self.assertIsNotNone(self.soup.find("span", id="summary-latency-modern"))
        self.assertIsNotNone(self.soup.find("div", id="classic-compare-content"))
        self.assertIsNotNone(self.soup.find("div", id="modern-compare-content"))

        # 2. Visão Moderna
        self.assertIsNotNone(self.soup.find("div", id="modern-results"))
        self.assertIsNotNone(self.soup.find("div", id="modern-hero-container"))
        self.assertIsNotNone(self.soup.find("div", id="modern-articles-container"))

        # 3. Visão Clássica
        self.assertIsNotNone(self.soup.find("div", id="classic-results"))
        self.assertIsNotNone(self.soup.find("span", id="classic-solo-latency"))
        self.assertIsNotNone(self.soup.find("div", id="classic-articles-container"))

        # 4. Controles Globais de Busca
        self.assertIsNotNone(self.soup.find("input", id="query-input"))
        self.assertIsNotNone(self.soup.find("select", id="top-k-select"))
        self.assertIsNotNone(self.soup.find("button", id="submit-btn"))
        self.assertIsNotNone(self.soup.find("div", id="skeleton-loader"))
        self.assertIsNotNone(self.soup.find("div", id="empty-state"))

    # =========================================================================
    # 3. VERIFICAÇÃO DOS 5 CHIPS DE EXEMPLO
    # =========================================================================

    def test_04_five_example_chips_exact_content_and_listeners(self):
        """Valida se os 5 chips contêm exatamente as perguntas esperadas e invocam setQueryAndSearch."""
        chips_container = self.soup.find("div", class_="chips-list")
        self.assertIsNotNone(chips_container, "Container .chips-list ausente.")

        chips = chips_container.find_all("button", class_="chip-pill")
        self.assertEqual(len(chips), 5, f"Esperado 5 chips, encontrados: {len(chips)}")

        expected_chips = [
            {
                "label": "Maioridade Civil (Art. 5º)",
                "query": "Com quantos anos a pessoa passa a ser plenamente capaz na vida civil?",
                "is_canonical": True,
                "is_refusal": False,
            },
            {
                "label": "Deveres no Casamento",
                "query": "Quais são os deveres dos cônjuges no casamento?",
                "is_canonical": False,
                "is_refusal": False,
            },
            {
                "label": "Personalidade Civil",
                "query": "Quando começa a personalidade civil da pessoa natural?",
                "is_canonical": False,
                "is_refusal": False,
            },
            {
                "label": "Prescrição Dano Moral",
                "query": "Qual o prazo para reparação civil por dano moral?",
                "is_canonical": False,
                "is_refusal": False,
            },
            {
                "label": "Teste de Abstenção (Fora de Escopo)",
                "query": "Receita de bolo de fubá com goiabada",
                "is_canonical": False,
                "is_refusal": True,
            },
        ]

        for i, expected in enumerate(expected_chips):
            chip = chips[i]
            text = chip.get_text(strip=True)
            self.assertIn(expected["label"], text, f"Label incorreto no chip {i+1}")

            onclick = chip.get("onclick", "")
            self.assertIn("setQueryAndSearch", onclick, f"Chip {i+1} não chama setQueryAndSearch")
            self.assertIn(expected["query"], onclick, f"Chip {i+1} não contém a query correta: {expected['query']}")

            classes = chip.get("class", [])
            if expected["is_canonical"]:
                self.assertIn("canonical-chip", classes)
            if expected["is_refusal"]:
                self.assertIn("refusal-chip", classes)

    # =========================================================================
    # 4. VALIDAÇÃO DE SINTAXE JS VIA NODE.JS RUNTIME
    # =========================================================================

    def test_05_javascript_syntax_and_compilation_with_node(self):
        """Extrai o bloco <script> e valida sintaxe via Node.js CLI ('node --check')."""
        scripts = self.soup.find_all("script")
        self.assertGreater(len(scripts), 0, "Nenhum bloco <script> encontrado no HTML.")

        full_js = "\n\n".join(s.string for s in scripts if s.string)
        self.assertGreater(len(full_js.strip()), 500, "Código JavaScript do template está vazio ou muito curto.")

        # Cria arquivo temporário para submeter ao node --check
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write(full_js)
            tmp_path = Path(tmp.name)

        try:
            res = subprocess.run(
                ["node", "--check", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Erro de sintaxe JavaScript detectado pelo Node.js:\n{res.stderr}",
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    # =========================================================================
    # 5. CONTRATO DE INTEGRAÇÃO JAVASCRIPT <-> API FASTAPI
    # =========================================================================

    def test_06_js_fetch_endpoints_exact_matching(self):
        """Verifica se todas as chamadas fetch() no JavaScript apontam para rotas ativas do backend."""
        scripts = self.soup.find_all("script")
        full_js = "\n\n".join(s.string for s in scripts if s.string)

        # Procura chamadas fetch('...') ou fetch("...")
        fetch_urls = re.findall(r"fetch\s*\(\s*['\"]([^'\"]+)['\"]", full_js)
        self.assertGreater(len(fetch_urls), 0, "Nenhuma chamada fetch detectada no JS.")

        # Rotas esperadas no contrato
        expected_active_routes = {
            "/models/status",
            "/health",
            "/search/compare",
            "/search/bert",
            "/search/tfidf",
        }

        # Todas as chamadas fetch devem ser rotas ativas conhecidas
        for url in fetch_urls:
            self.assertIn(
                url,
                expected_active_routes,
                f"Chamada fetch para endpoint desconhecido ou inexistente: '{url}'",
            )

        # E todas as rotas esperadas de busca devem estar presentes no JS
        for required_route in ["/search/compare", "/search/bert", "/search/tfidf", "/models/status"]:
            self.assertIn(
                required_route,
                fetch_urls,
                f"Rota essencial '{required_route}' não chamada em nenhum fetch no JavaScript.",
            )

    def test_07_js_payloads_match_query_request_schema(self):
        """Verifica se os dados enviados nos requests POST respeitam o schema QueryRequest(query, top_k)."""
        scripts = self.soup.find_all("script")
        full_js = "\n\n".join(s.string for s in scripts if s.string)

        # Busca chamadas JSON.stringify
        json_stringify_calls = re.findall(r"JSON\.stringify\s*\(\s*\{([^}]+)\}\s*\)", full_js)
        self.assertGreater(len(json_stringify_calls), 0)

        for payload_content in json_stringify_calls:
            # Deve conter query e top_k
            self.assertIn("query", payload_content, "Payload enviado via fetch não contém 'query'")
            self.assertIn("top_k", payload_content, "Payload enviado via fetch não contém 'top_k'")

        # Valida instanciando o schema Pydantic oficial
        valid_payload = QueryRequest(query="Teste de integração", top_k=3)
        self.assertEqual(valid_payload.query, "Teste de integração")
        self.assertEqual(valid_payload.top_k, 3)

    def test_08_js_consumed_properties_match_pydantic_schemas(self):
        """Verifica se todas as propriedades de resposta manipuladas no JS existem nos schemas Pydantic do backend."""
        scripts = self.soup.find_all("script")
        full_js = "\n\n".join(s.string for s in scripts if s.string)

        # Schemas do backend:
        # SearchTfidfResponse: model, query, results, execution_time_ms
        # ClassicArticleResult: artigo_id, citacao, texto, score
        # SearchBertResponse: model, query, resposta_gerada, abstenção, abstencao, results, execution_time_ms
        # BertArticleResult: artigo_id, citacao, texto, similarity_score
        # CompareResponse: query, classico, moderno, comparacao

        expected_properties = [
            ("results", ["SearchTfidfResponse", "SearchBertResponse"]),
            ("artigo_id", ["ClassicArticleResult", "BertArticleResult"]),
            ("citacao", ["ClassicArticleResult", "BertArticleResult"]),
            ("texto", ["ClassicArticleResult", "BertArticleResult"]),
            ("score", ["ClassicArticleResult"]),
            ("similarity_score", ["BertArticleResult"]),
            ("resposta_gerada", ["SearchBertResponse"]),
            ("execution_time_ms", ["SearchTfidfResponse", "SearchBertResponse"]),
            ("classico", ["CompareResponse", "ModelStatusResponse"]),
            ("moderno", ["CompareResponse", "ModelStatusResponse"]),
        ]

        for prop, schemas in expected_properties:
            self.assertTrue(
                re.search(rf"\b{prop}\b", full_js),
                f"Propriedade de contrato '{prop}' ({', '.join(schemas)}) não referenciada no JavaScript.",
            )

        # Verifica tratamento robusto de abstenção com e sem acento no JS
        self.assertTrue(
            "abstenção" in full_js and "abstencao" in full_js,
            "JavaScript deve verificar tanto 'abstenção' quanto 'abstencao' para compatibilidade de clientes.",
        )

    # =========================================================================
    # 6. RESILIÊNCIA OFFLINE E AUTONOMIA (CSS & ASSETS)
    # =========================================================================

    def test_09_offline_resilience_no_external_resources(self):
        """Valida que o HTML/CSS/JS não realiza nenhuma requisição externa a CDNs ou APIs de terceiros."""
        # 1. Busca por URLs http:// ou https://
        external_urls = re.findall(r"https?://[^\s\"\'\<\>]+", self.html_content)
        self.assertEqual(
            external_urls,
            [],
            f"URLs externas encontradas no template (violação de autonomia offline): {external_urls}",
        )

        # 2. Busca por @import no CSS
        imports = re.findall(r"@import\s+[^;]+;", self.html_content)
        self.assertEqual(imports, [], f"@import externo encontrado no CSS: {imports}")

        # 3. Busca por tags <link rel="stylesheet"> externas
        link_styles = self.soup.find_all("link", rel="stylesheet")
        self.assertEqual(link_styles, [], f"<link rel='stylesheet'> remoto detectado: {link_styles}")

        # 4. Busca por <script src="..."> externos
        script_srcs = [s.get("src") for s in self.soup.find_all("script") if s.get("src")]
        self.assertEqual(script_srcs, [], f"<script src='...'> remoto detectado: {script_srcs}")

        # 5. Fontes locais do sistema
        style_content = "\n".join(s.string for s in self.soup.find_all("style") if s.string)
        self.assertIn("font-family", style_content)
        self.assertIn("-apple-system", style_content)
        self.assertIn("sans-serif", style_content)

    # =========================================================================
    # 7. SEGURANÇA E HIGIENIZAÇÃO XSS
    # =========================================================================

    def test_10_xss_protection_escape_html(self):
        """Verifica a presença da função escapeHtml() e que ela sanitiza caracteres perigosos."""
        scripts = self.soup.find_all("script")
        full_js = "\n\n".join(s.string for s in scripts if s.string)

        self.assertIn("function escapeHtml(str)", full_js, "Função escapeHtml() de mitigação XSS ausente.")
        self.assertIn("&amp;", full_js)
        self.assertIn("&lt;", full_js)
        self.assertIn("&gt;", full_js)
        self.assertIn("&quot;", full_js)
        self.assertIn("&#039;", full_js)

        # Testa a execução de escapeHtml com payload malicioso via Node.js
        test_script = f"""
        global.document = {{
            getElementById: () => ({{ addEventListener: () => {{}}, style: {{}} }}),
            addEventListener: () => {{}}
        }};
        global.window = {{}};
        {full_js}
        const payload = '<script>alert("XSS")</script>&"\\'';
        const escaped = escapeHtml(payload);
        if (escaped.includes('<script>') || escaped.includes('"') || escaped.includes("'")) {{
            console.error("FALHA NA ESCAPAGEM:", escaped);
            process.exit(1);
        }}
        process.stdout.write(escaped);
        """
        res = subprocess.run(
            ["node", "-e", test_script],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Falha no teste unitário do escapeHtml: {res.stderr}")
        self.assertNotIn("<script>", res.stdout)
        self.assertIn("&lt;script&gt;", res.stdout)

    # =========================================================================
    # 8. INTEGRAÇÃO AO VIVO VIA TESTCLIENT (GET /)
    # =========================================================================

    def test_11_get_root_endpoint_live_response_and_headers(self):
        """Valida que GET / servido pelo FastAPI retorna HTTP 200, UTF-8 e o mesmo HTML verificado."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("charset=utf-8", response.headers.get("content-type", "").lower())

        # O corpo servido ao vivo deve coincidir com o template em disco
        self.assertEqual(response.text, self.html_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
