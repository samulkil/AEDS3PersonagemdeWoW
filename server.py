from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import os
import re
import mimetypes
import socketserver

# Importação dos DAOs e Modelos
from dao.ContaDAO import ContaDAO
from model.Conta import Conta
from dao.PersonagemDAO import PersonagemDAO
from model.Personagem import Personagem
from dao.GrupoTempDAO import GrupoTempDAO
from dao.BairroDAO import BairroDAO
from model.Bairro import Bairro

HOST = "localhost"
PORT = 8001

# Instância global para persistência em memória (volátil)
dao_grupo = GrupoTempDAO()

class Servidor(BaseHTTPRequestHandler):
    
    # --- UTILITÁRIOS ---

    def _avaliar_condicional(self, chave, contexto):
        """Avalia se uma variável do contexto deve ser tratada como verdadeira."""
        if chave not in contexto:
            return False

        valor = contexto.get(chave)
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, (int, float)):
            return valor != 0

        texto = str(valor).strip().lower()
        return texto not in ('', 'false', '0', 'none', 'null')

    def _processar_condicionais(self, conteudo, contexto):
        """Processa blocos {% if %}, {% else %} e {% endif %} do template."""
        tag_if = re.compile(r'{%\s*if\s+(\w+)\s*%}')
        tag_else = re.compile(r'{%\s*else\s*%}')
        tag_endif = re.compile(r'{%\s*endif\s*%}')

        while tag_if.search(conteudo):
            match = tag_if.search(conteudo)
            chave = match.group(1)
            cursor = match.end()
            profundidade = 1
            else_inicio = else_fim = None
            endif_inicio = endif_fim = None

            while cursor < len(conteudo) and profundidade > 0:
                candidatos = []
                for padrao, tipo in ((tag_if, 'if'), (tag_else, 'else'), (tag_endif, 'endif')):
                    proximo = padrao.search(conteudo, cursor)
                    if proximo:
                        candidatos.append((proximo.start(), tipo, proximo))

                if not candidatos:
                    break

                _, tipo, proximo = min(candidatos, key=lambda item: item[0])

                if tipo == 'if':
                    profundidade += 1
                    cursor = proximo.end()
                elif tipo == 'else' and profundidade == 1 and else_inicio is None:
                    else_inicio = proximo.start()
                    else_fim = proximo.end()
                    cursor = proximo.end()
                elif tipo == 'endif':
                    profundidade -= 1
                    if profundidade == 0:
                        endif_inicio = proximo.start()
                        endif_fim = proximo.end()
                    else:
                        cursor = proximo.end()
                else:
                    cursor = proximo.end()

            if endif_inicio is None:
                break

            fim_bloco_if = else_inicio if else_inicio is not None else endif_inicio
            bloco_if = conteudo[match.end():fim_bloco_if]
            bloco_else = conteudo[else_fim:endif_inicio] if else_inicio is not None else ''
            substituto = bloco_if if self._avaliar_condicional(chave, contexto) else bloco_else
            conteudo = conteudo[:match.start()] + substituto + conteudo[endif_fim:]

        return conteudo
    
    def _render_template(self, nome_arquivo, contexto=None):
        if contexto is None: contexto = {}
        template_path = f'templates/{nome_arquivo}'
        
        if not os.path.exists(template_path):
            return f"<h1>Erro: Template {nome_arquivo} não encontrado</h1>"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Processa herança ({% extends %})
        extends_match = re.search(r'{%\s*extends\s+"([^"]+)"\s*%}', conteudo)
        if extends_match:
            base_template = extends_match.group(1)
            blocos = {}
            padrao_bloco = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
            for match in re.finditer(padrao_bloco, conteudo, re.DOTALL):
                blocos[match.group(1)] = match.group(2)
            
            with open(f'templates/{base_template}', 'r', encoding='utf-8') as f:
                conteudo = f.read()
            for nome_bloco, conteudo_bloco in blocos.items():
                padrao = r'{%\s*block\s+' + nome_bloco + r'\s*%}.*?{%\s*endblock\s*%}'
                conteudo = re.sub(padrao, conteudo_bloco, conteudo, flags=re.DOTALL)
        
        # Processa includes ({% include %})
        conteudo = re.sub(r'{%\s*include\s+"([^"]+)"\s*%}', 
                         lambda m: open(f"templates/{m.group(1)}", 'r', encoding='utf-8').read(), 
                         conteudo)

        # Processa condicionais ({% if %}, {% else %}, {% endif %})
        conteudo = self._processar_condicionais(conteudo, contexto)
        
        # Substitui variáveis ({{variavel}})
        for chave, valor in contexto.items():
            padrao_safe = r'{{\s*' + chave + r'\s*\|\s*safe\s*}}'
            if re.search(padrao_safe, conteudo):
                conteudo = re.sub(padrao_safe, str(valor), conteudo)
            else:
                valor_escapado = str(valor).replace('<', '&lt;').replace('>', '&gt;')
                padrao = r'{{\s*' + chave + r'\s*}}'
                conteudo = re.sub(padrao, valor_escapado, conteudo)
        
        return conteudo

    def _set_cookie(self, nome, valor):
        self.send_header('Set-Cookie', f'{nome}={valor}; Path=/; HttpOnly')
            
    def _get_cookie(self, nome):
        if 'Cookie' in self.headers:
            for cookie in self.headers['Cookie'].split('; '):
                if '=' in cookie:
                    chave, valor = cookie.split('=', 1)
                    if chave == nome: return valor
        return None

    def _get_usuario_logado(self):
        id_conta = self._get_cookie('id_conta')
        usuario = self._get_cookie('usuario')
        if id_conta and usuario:
            dao = ContaDAO()
            conta = dao.read(int(id_conta))
            if conta and conta.lapide == b' ':
                return {'id': int(id_conta), 'usuario': usuario}
        return None

    def _gerar_linhas_personagens(self, id_conta):
        """Usa o relacionamento 1:N via Hash Extensível para listar personagens."""
        dao = PersonagemDAO()
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        # Método indexado via Hash
        dao.listar_por_conta(id_conta)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        linhas_html = ""
        if output.strip():
            for linha in output.strip().split('\n'):
                if '|' in linha:
                    p = [part.strip() for part in linha.split('|')]
                    if len(p) >= 4:
                        # Gera linhas para a tabela com colunas: ID, Nome, Nível, Função
                        linhas_html += f"<tr><td>{p[0]}</td><td>{p[1]}</td><td>{p[2]}</td><td>{p[3]}</td>"
                        linhas_html += f"<td><a href='/editar_personagem?id={p[0]}' class='wow-link'>✏️ Editar</a> "
                        linhas_html += f"<a href='/excluir_personagem?id={p[0]}' class='wow-link wow-link-danger' onclick='return confirm(\"Excluir?\");'>🗑️ Excluir</a></td></tr>"
        return linhas_html

    def _gerar_visualizacao_bplus_id(self, id_busca=None):
        """Monta uma visualização estruturada da Árvore B+ (índice por ID)."""
        try:
            dao = PersonagemDAO()
            arvore = dao.arvore_id
            raiz = arvore._ler_raiz()
            if raiz == -1:
                return "<p class='wow-note'>Árvore B+ vazia.</p>"

            html = []
            fila = [(raiz, 0)]
            visitados = set()
            niveis = {}

            while fila:
                offset, nivel = fila.pop(0)
                if offset in visitados:
                    continue
                visitados.add(offset)

                no = arvore._ler_no(offset)
                tipo = "Folha" if no.eh_folha else "Interno"
                chaves = ", ".join(str(c) for c in no.chaves) if no.chaves else "vazio"
                destaque = ""
                if id_busca is not None and no.eh_folha and id_busca in no.chaves:
                    destaque = " wow-bplus-node-highlight"
                cartao = (
                    f"<article class='wow-card wow-bplus-node{destaque}'>"
                    f"<div class='wow-bplus-node-badge'>{tipo}</div>"
                    f"<div class='wow-bplus-node-meta'>offset: {offset}</div>"
                    f"<div class='wow-bplus-node-keys'>chaves: [{chaves}]</div>"
                    + (f"<div class='wow-bplus-node-next'>proximo: {no.proximo}</div>" if no.eh_folha else "")
                    + "</article>"
                )
                niveis.setdefault(nivel, []).append(cartao)

                if not no.eh_folha:
                    for filho in no.ponteiros:
                        if filho not in (None, -1, 0):
                            fila.append((filho, nivel + 1))

            html.append("<section class='wow-bplus-tree'>")
            for nivel in sorted(niveis.keys()):
                html.append("<div class='wow-bplus-level'>")
                html.append(f"<div class='wow-note wow-bplus-level-title'><strong>Nível {nivel}</strong></div>")
                html.append("<div class='wow-bplus-level-nodes'>")
                html.extend(niveis[nivel])
                html.append("</div></div>")
            html.append("</section>")

            # Cadeia de folhas (ordem da esquerda para direita)
            no = arvore._ler_no(raiz)
            while not no.eh_folha and no.ponteiros:
                no = arvore._ler_no(no.ponteiros[0])

            folhas = []
            while no:
                classe_folha = ""
                if id_busca is not None and id_busca in no.chaves:
                    classe_folha = " wow-bplus-leaf-chain-item-highlight"
                folhas.append(
                    f"<span class='wow-bplus-leaf-chain-item{classe_folha}'>"
                    + "[" + ", ".join(str(c) for c in no.chaves) + "]"
                    + "</span>"
                )
                if no.proximo in (-1, None):
                    break
                no = arvore._ler_no(no.proximo)

            if folhas:
                html.append("<div class='wow-card wow-bplus-leaf-chain'>")
                html.append(
                    "<div class='wow-note'><strong>Encadeamento das folhas:</strong> "
                    + "<span class='wow-bplus-leaf-chain-track'>"
                    + " <span class='wow-bplus-leaf-chain-arrow'>→</span> ".join(folhas)
                    + "</span></div>"
                )
                html.append("</div>")

            return "".join(html)
        except Exception as e:
            return f"<p class='wow-note'>Não foi possível renderizar a Árvore B+: {e}</p>"

    def _gerar_linhas_personagens_selecao_grupo(self, id_conta):
        """Gera linhas de seleção com radio pronto para criar/entrar em grupo."""
        dao = PersonagemDAO()
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        dao.listar_por_conta(id_conta)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        linhas_html = ""
        if output.strip():
            for linha in output.strip().split('\n'):
                if '|' not in linha:
                    continue
                p = [part.strip() for part in linha.split('|')]
                if len(p) >= 4:
                    try:
                        id_p = int(p[0])
                    except ValueError:
                        continue
                    linhas_html += (
                        f"<tr><td><input type='radio' name='id_p' value='{id_p}' required></td>"
                        f"<td>{id_p}</td><td>{p[1]}</td><td>{p[3]}</td></tr>"
                    )
        return linhas_html

    def _bairro_pertence_conta(self, bairro, id_conta):
        """Verifica se o personagem dono do bairro pertence à conta logada."""
        if not bairro:
            return False
        p = PersonagemDAO().read_by_id_and_conta(bairro.id_dono, id_conta)
        return p is not None

    def _gerar_opcoes_personagens_dono(self, id_conta, id_selecionado=None):
        """Gera <option> para escolher o personagem dono do bairro."""
        dao = PersonagemDAO()
        import io, sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        dao.listar_por_conta(id_conta)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        opcoes = ""
        if output.strip():
            for linha in output.strip().split('\n'):
                if '|' not in linha:
                    continue
                p = [part.strip() for part in linha.split('|')]
                if len(p) < 4:
                    continue
                try:
                    id_p = int(p[0])
                except ValueError:
                    continue
                selected = ' selected' if id_selecionado is not None and id_p == id_selecionado else ''
                opcoes += f"<option value='{id_p}'{selected}>{p[0]} - {p[1]} ({p[3]})</option>"

        if not opcoes:
            opcoes = "<option value='' disabled selected>Nenhum personagem disponível</option>"
        return opcoes

    def _gerar_linhas_bairros(self, id_conta):
        """Gera linhas de bairros para exibição na página web."""
        dao_bairro = BairroDAO()
        dao_perso = PersonagemDAO()
        dao_conta = ContaDAO()

        bairros = dao_bairro.listar_todos_objetos()
        linhas_html = ""

        for b in bairros:
            nome_limpo = b.nome.decode('utf-8').strip('\x00')
            p_dono = dao_perso.read(b.id_dono)
            nome_usuario_dono = "???"
            if p_dono:
                conta_dono = dao_conta.read(p_dono.id_conta)
                if conta_dono:
                    nome_usuario_dono = conta_dono.usuario.decode('utf-8').strip('\x00')

            acoes = f"<a href='/bairros_personagens?id={b.id}' class='wow-link'>Ver personagens</a>"
            if self._bairro_pertence_conta(b, id_conta):
                acoes += (
                    f" <a href='/editar_bairro?id={b.id}' class='wow-link'>✏️ Editar</a>"
                    f" <a href='/excluir_bairro?id={b.id}' class='wow-link wow-link-danger'"
                    f" onclick='return confirm(\"Excluir este bairro?\");'>🗑️ Excluir</a>"
                )

            linhas_html += (
                f"<tr>"
                f"<td>{b.id}</td>"
                f"<td>{nome_limpo}</td>"
                f"<td>{nome_usuario_dono}</td>"
                f"<td>{acoes}</td>"
                f"</tr>"
            )

        if not linhas_html:
            linhas_html = "<tr><td colspan='4'>Nenhum bairro cadastrado.</td></tr>"

        return linhas_html

    def _gerar_todos_personagens_selecao(self):
        """Retorna linhas HTML com todos os personagens de todas as contas para seleção."""
        dao_p = PersonagemDAO()
        dao_c = ContaDAO()
        personagens = dao_p.listar_todos_objetos() if hasattr(dao_p, 'listar_todos_objetos') else []

        # Fallback: varredura direta se não houver método dedicado
        if not personagens:
            import struct, os
            reg_size = struct.calcsize(dao_p.formato) if hasattr(dao_p, 'formato') else 51
            try:
                from model.Personagem import Personagem as _P
                reg_size = struct.calcsize(_P.FORMATO)
                with open(dao_p.arquivo, "rb") as f:
                    f.seek(dao_p.header_size)
                    while True:
                        dados = f.read(reg_size)
                        if len(dados) != reg_size:
                            break
                        p = _P.from_bytes(dados)
                        if p.lapide == b' ':
                            personagens.append(p)
            except Exception:
                pass

        linhas = ""
        for p in personagens:
            nome_p = p.nome.decode('utf-8').strip('\x00')
            func_p = p.funcao.decode('utf-8').strip('\x00')
            conta = dao_c.read(p.id_conta)
            usuario_p = conta.usuario.decode('utf-8').strip('\x00') if conta else f"conta {p.id_conta}"
            linhas += (
                f"<tr>"
                f"<td><input type='radio' name='id_p' value='{p.id}' required></td>"
                f"<td>{p.id}</td>"
                f"<td>{nome_p}</td>"
                f"<td>{func_p}</td>"
                f"<td>{usuario_p}</td>"
                f"</tr>"
            )
        return linhas or "<tr><td colspan='5'>Nenhum personagem cadastrado.</td></tr>"

    def _gerar_linhas_personagens_bairro(self, id_bairro, pode_gerenciar=False, id_conta_logada=None):
        """Lista personagens de um bairro em formato de tabela HTML."""
        dao_bairro = BairroDAO()
        dao_perso = PersonagemDAO()
        dao_conta = ContaDAO()

        import io, sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        dao_bairro.listar_personagens_do_bairro(id_bairro)

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        linhas_html = ""
        for linha in output.strip().split("\n"):
            partes = linha.strip().split(":")
            if len(partes) != 2:
                continue
            try:
                id_p = int(partes[1].strip())
            except ValueError:
                continue

            p = dao_perso.read(id_p)
            if not p:
                continue

            nome_p = p.nome.decode('utf-8').strip('\x00')
            func_p = p.funcao.decode('utf-8').strip('\x00')
            nivel_p = p.nivel
            conta_p = dao_conta.read(p.id_conta)
            usuario_p = conta_p.usuario.decode('utf-8').strip('\x00') if conta_p else f"conta {p.id_conta}"

            # Dono do bairro pode remover qualquer personagem
            eh_dono_perso = (id_conta_logada is not None and p.id_conta == id_conta_logada)

            acoes = ""
            if pode_gerenciar:
                acoes = (
                    f"<a href='/remover_personagem_bairro?id_bairro={id_bairro}&id_personagem={id_p}' "
                    f"class='wow-link wow-link-danger' onclick='return confirm(\"Remover do bairro?\");'>Remover</a>"
                )
            elif eh_dono_perso:
                acoes = (
                    f"<a href='/sair_do_bairro?id_bairro={id_bairro}&id_personagem={id_p}' "
                    f"class='wow-link wow-link-danger' onclick='return confirm(\"Sair deste bairro?\");'>Sair</a>"
                )

            linhas_html += (
                f"<tr>"
                f"<td>{id_p}</td>"
                f"<td>{nome_p}</td>"
                f"<td>{nivel_p}</td>"
                f"<td>{func_p}</td>"
                f"<td>{usuario_p}</td>"
                f"<td>{acoes}</td>"
                f"</tr>"
            )

        if not linhas_html:
            linhas_html = "<tr><td colspan='6'>Este bairro não possui personagens.</td></tr>"

        return linhas_html

    # --- ROTAS GET ---

    def do_GET(self):
        usuario_logado = self._get_usuario_logado()
        url_parseada = urllib.parse.urlparse(self.path)
        # CORREÇÃO DO ERRO 404: Normalização do caminho
        caminho = url_parseada.path.rstrip('/') or '/'
        params = urllib.parse.parse_qs(url_parseada.query)

        # Arquivos Estáticos e Imagens
        if caminho.startswith(("/static", "/imagens")):
            folder = "static" if "/static" in caminho else "imagens"
            path_parts = caminho.split(f"/{folder}/")
            if len(path_parts) > 1:
                rel_path = path_parts[-1]
                file_path = os.path.join("templates", folder, rel_path)
                if os.path.isfile(file_path):
                    self.send_response(200)
                    self.send_header("Content-type", mimetypes.guess_type(file_path)[0] or "application/octet-stream")
                    self.end_headers()
                    with open(file_path, "rb") as f: self.wfile.write(f.read())
                    return
            self.send_error(404)
            return

        # Roteamento de Páginas
        if caminho == "/":
            self.send_response(200)
            self.end_headers()
            html = self._render_template('home_logado.html', {'usuario': usuario_logado['usuario']}) if usuario_logado else self._render_template('home.html')
            self.wfile.write(html.encode())

        elif caminho == "/personagens":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('personagens.html', {
                'usuario': usuario_logado['usuario'], 
                'personagens': self._gerar_linhas_personagens(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        elif caminho == "/bairros":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('bairros.html', {
                'usuario': usuario_logado['usuario'],
                'bairros': self._gerar_linhas_bairros(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        elif caminho == "/criar_bairro":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_bairro.html', {
                'usuario': usuario_logado['usuario'],
                'opcoes_dono': self._gerar_opcoes_personagens_dono(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        elif caminho == "/editar_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_b = int(params.get('id', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("ID inválido", "Informe um ID de bairro válido.", "/bairros", "Voltar")
            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_b)
            if not bairro or not self._bairro_pertence_conta(bairro, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "Você só pode editar bairros dos seus personagens.", "/bairros", "Voltar")
            nome_b = bairro.nome.decode('utf-8').strip('\x00')
            self.send_response(200)
            self.end_headers()
            html = self._render_template('editar_bairro.html', {
                'usuario': usuario_logado['usuario'],
                'id': bairro.id,
                'nome': nome_b,
                'opcoes_dono': self._gerar_opcoes_personagens_dono(usuario_logado['id'], bairro.id_dono)
            })
            self.wfile.write(html.encode())

        elif caminho == "/excluir_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_b = int(params.get('id', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("ID inválido", "Informe um ID de bairro válido.", "/bairros", "Voltar")
            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_b)
            if bairro and self._bairro_pertence_conta(bairro, usuario_logado['id']):
                dao_bairro.delete(id_b)
            self._redirect("/bairros")

        elif caminho == "/arvore_bplus":
            if not usuario_logado: return self._redirect("/login")

            id_busca_param = params.get('id_busca', [""])[0].strip()
            id_busca_valor = None
            mensagem_busca = ""

            if id_busca_param:
                try:
                    id_busca_valor = int(id_busca_param)
                    dao_p = PersonagemDAO()
                    personagem = dao_p.read_bplus(id_busca_valor)
                    if personagem:
                        nome = personagem.nome.decode('utf-8').strip('\x00')
                        funcao = personagem.funcao.decode('utf-8').strip('\x00')
                        mensagem_busca = f"Personagem encontrado no índice B+: ID {personagem.id}, {nome} ({funcao}), nível {personagem.nivel:.2f}."
                    else:
                        mensagem_busca = f"Nenhum personagem com ID {id_busca_valor} foi encontrado no índice B+."
                except ValueError:
                    mensagem_busca = "Informe um ID numérico válido para buscar na Árvore B+."

            self.send_response(200)
            self.end_headers()
            html = self._render_template('arvore_bplus.html', {
                'usuario': usuario_logado['usuario'],
                'visualizacao_bplus': self._gerar_visualizacao_bplus_id(id_busca_valor),
                'id_busca': id_busca_param,
                'mensagem_busca': mensagem_busca
            })
            self.wfile.write(html.encode())

        # --- SISTEMA DE GRUPOS ---
        
        elif caminho == "/grupos" or caminho == "/group":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            
            lista_html = ""
            for id_g in dao_grupo.grupos_criados:
                membros = dao_grupo.listar_membros_do_grupo(id_g)
                lista_html += f"""<div class='wow-card'><div class='wow-card-title'>Grupo #{id_g} ({len(membros)}/5)</div>
                                  <div class='wow-actions' style='justify-content: flex-start;'>
                                  <a href='/detalhes_grupo?id={id_g}' class='wow-btn'>Ver Detalhes</a>
                                  <a href='/selecionar_personagem_grupo?id={id_g}' class='wow-btn wow-btn-success'>Entrar</a></div></div>"""
            
            html = self._render_template('group.html', {
                'usuario': usuario_logado['usuario'], 
                'lista_grupos': lista_html or "<p>Nenhum grupo ativo no momento.</p>"
            })
            self.wfile.write(html.encode())

        elif caminho == "/detalhes_grupo":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_g = int(params.get('id', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("ID inválido", "Informe um ID de grupo válido para ver os detalhes.", "/grupos", "Voltar")
            membros = dao_grupo.listar_membros_do_grupo(id_g)
            
            linhas = ""
            dao_p = PersonagemDAO()
            dao_c = ContaDAO()
            for m in membros:
                p = dao_p.read(m.id_personagem) # Busca via Hash PK
                if p:
                    f_str = p.funcao.decode().strip('\x00')
                    n_str = p.nome.decode().strip('\x00')
                    conta = dao_c.read(m.id_conta)
                    usuario = conta.usuario if conta else f"Conta {m.id_conta}"
                    linhas += f"<tr><td>{usuario}</td><td>{m.id_personagem}</td><td>{n_str}</td><td>{f_str}</td></tr>"
            
            self.send_response(200)
            self.end_headers()
            html = self._render_template('detalhes_grupo.html', {'id_grupo': id_g, 'linhas_membros': linhas})
            self.wfile.write(html.encode())

        elif caminho == "/selecionar_personagem_grupo":
            if not usuario_logado: return self._redirect("/login")
            id_g = int(params.get('id', [0])[0])
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_grupo_selecao.html', {
                'usuario': usuario_logado['usuario'],
                'id_grupo': id_g,
                'personagens': self._gerar_linhas_personagens_selecao_grupo(usuario_logado['id']),
                'titulo_grupo': f"Juntar-se ao Grupo #{id_g}",
                'form_action': f"/entrar_no_grupo_final?id_g={id_g}"
            })
            self.wfile.write(html.encode())

        elif caminho == "/entrar_no_grupo_final":
            if not usuario_logado: return self._redirect("/login")
            # Esta rota é processada via POST (formulário). Em GET, apenas redireciona.
            self._redirect("/grupos")

        elif caminho == "/criar_grupo_web":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_grupo_selecao.html', {
                'usuario': usuario_logado['usuario'],
                'id_grupo': 0, # Indica que é criação de novo grupo
                'personagens': self._gerar_linhas_personagens_selecao_grupo(usuario_logado['id']),
                'titulo_grupo': "Iniciar Nova Jornada",
                'form_action': "/processar_criacao_grupo"
            })
            self.wfile.write(html.encode())

        # Rotas de Cadastro/Login
        elif caminho == "/criar_conta":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._render_template('criar_conta.html').encode())

        elif caminho == "/login":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._render_template('login.html').encode())

        elif caminho == "/logout":
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.send_header('Set-Cookie', 'usuario=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()

        elif caminho == "/excluir_personagem":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(params.get('id', [0])[0])
            dao = PersonagemDAO()
            p = dao.read(id_p)
            if p and p.id_conta == usuario_logado['id']:
                dao.delete(id_p)
            self._redirect("/personagens")

        elif caminho == "/editar_personagem":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(params.get('id', [0])[0])
            p = PersonagemDAO().read(id_p)
            if not p or p.id_conta != usuario_logado['id']: return self.send_error(403)
            
            nome_p = p.nome.decode('utf-8').strip('\x00')
            func_p = p.funcao.decode('utf-8').strip('\x00')
            self.send_response(200)
            self.end_headers()
            html = self._render_template('editar_personagem.html', {
                'id': p.id, 'nome': nome_p, 'nivel': p.nivel, 'usuario': usuario_logado['usuario'],
                'selected_dano': 'selected' if func_p == 'dano' else '',
                'selected_tanque': 'selected' if func_p == 'tanque' else '',
                'selected_suporte': 'selected' if func_p == 'suporte' else ''
            })
            self.wfile.write(html.encode())

        elif caminho == "/criar_personagem":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._render_template('criar_personagem.html', {'usuario': usuario_logado['usuario']}).encode())

        elif caminho == "/config_conta":
            if not usuario_logado: return self._redirect("/login")
            dao = ContaDAO()
            conta = dao.read(usuario_logado['id'])
            if not conta:
                return self._render_mensagem("Conta não encontrada", "Não foi possível carregar suas configurações.", "/personagens", "Voltar")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('config_conta.html', {
                'id': conta.id,
                'usuario': conta.usuario,
                'email': conta.email,
                'data': conta.data
            })
            self.wfile.write(html.encode())

        elif caminho == "/bairros_personagens":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_bairro = int(params.get('id', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem(
                    "Bairro inválido",
                    "Informe um ID de bairro válido.",
                    "/bairros",
                    "Voltar"
                )

            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_bairro)
            if not bairro:
                return self._render_mensagem(
                    "Bairro não encontrado",
                    "Não foi possível localizar o bairro informado.",
                    "/bairros",
                    "Voltar"
                )

            nome_bairro = bairro.nome.decode('utf-8').strip('\x00')
            pode_gerenciar = self._bairro_pertence_conta(bairro, usuario_logado['id'])

            self.send_response(200)
            self.end_headers()
            html = self._render_template('bairros_personagens.html', {
                'usuario': usuario_logado['usuario'],
                'nome_bairro': nome_bairro,
                'id_bairro': id_bairro,
                'pode_gerenciar': "true" if pode_gerenciar else "",
                'personagens_bairro': self._gerar_linhas_personagens_bairro(
                    id_bairro, pode_gerenciar, usuario_logado['id']
                )
            })
            self.wfile.write(html.encode())

        elif caminho == "/selecionar_personagem_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_bairro = int(params.get('id', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Bairro inválido", "Informe um ID de bairro válido.", "/bairros", "Voltar")

            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_bairro)
            if not bairro or not self._bairro_pertence_conta(bairro, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "Você só pode gerenciar personagens em bairros dos seus personagens.", f"/bairros_personagens?id={id_bairro}", "Voltar")

            nome_bairro = bairro.nome.decode('utf-8').strip('\x00')

            self.send_response(200)
            self.end_headers()
            html = self._render_template('selecionar_personagem_bairro.html', {
                'usuario': usuario_logado['usuario'],
                'nome_bairro': nome_bairro,
                'id_bairro': id_bairro,
                'personagens': self._gerar_todos_personagens_selecao(),
                'form_action': f"/adicionar_personagem_bairro?id_bairro={id_bairro}"
            })
            self.wfile.write(html.encode())

        elif caminho == "/remover_personagem_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_bairro = int(params.get('id_bairro', [0])[0])
                id_personagem = int(params.get('id_personagem', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Erro", "Parâmetros inválidos.", "/bairros", "Voltar")

            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_bairro)
            if not bairro or not self._bairro_pertence_conta(bairro, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "Somente o dono do bairro pode remover personagens.", f"/bairros_personagens?id={id_bairro}", "Voltar")

            dao_bairro.remover_personagem(id_bairro, id_personagem)
            self._redirect(f"/bairros_personagens?id={id_bairro}")

        elif caminho == "/sair_do_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_bairro = int(params.get('id_bairro', [0])[0])
                id_personagem = int(params.get('id_personagem', [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Erro", "Parâmetros inválidos.", "/bairros", "Voltar")

            # Verifica que o personagem pertence à conta logada
            p = PersonagemDAO().read_by_id_and_conta(id_personagem, usuario_logado['id'])
            if not p:
                return self._render_mensagem("Acesso negado", "Este personagem não pertence à sua conta.", f"/bairros_personagens?id={id_bairro}", "Voltar")

            BairroDAO().remover_personagem(id_bairro, id_personagem)
            self._redirect(f"/bairros_personagens?id={id_bairro}")

        elif caminho == "/confirmar_excluir_conta":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('confirmar_excluir_conta.html', {
                'usuario': usuario_logado['usuario'],
                'id': usuario_logado['id']
            })
            self.wfile.write(html.encode())

        else: self.send_error(404)

    # --- ROTAS POST ---

    def do_POST(self):
        usuario_logado = self._get_usuario_logado()
        url_parseada = urllib.parse.urlparse(self.path)
        caminho = url_parseada.path.rstrip('/') or '/'
        
        tamanho = int(self.headers['Content-Length'])
        parametros = urllib.parse.parse_qs(self.rfile.read(tamanho).decode())

        if caminho == "/salvar_conta":
            u = parametros.get("usuario", [""])[0]
            e = parametros.get("email", [""])[0]
            d = parametros.get("data", [""])[0]
            s = parametros.get("senha", [""])[0]
            if not s:
                return self._render_mensagem("Erro!", "A senha não pode ser vazia.", "/criar_conta", "Voltar")
            dao = ContaDAO()
            if dao.read_por_usuario(u):
                return self._render_mensagem("Erro!", "Nome de usuário já existe.", "/criar_conta", "Voltar")
            nova_conta = Conta(0, u, e, d)
            nova_conta.set_senha(s)
            dao.create(nova_conta)
            self._render_mensagem("Sucesso!", f"Conta de {u} criada!", "/", "Ir para início")

        elif caminho == "/autenticar":
            u = parametros.get("usuario", [""])[0]
            s = parametros.get("senha", [""])[0]
            conta = ContaDAO().read_por_usuario(u)
            if conta and conta.lapide == b' ' and conta.verificar_senha(s):
                self.send_response(302)
                self.send_header('Location', '/personagens')
                self._set_cookie('id_conta', str(conta.id))
                self._set_cookie('usuario', conta.usuario)
                self.end_headers()
            else:
                self._render_mensagem("Acesso Negado!", "Usuário ou senha inválidos.", "/login", "Tentar novamente")

        elif caminho == "/salvar_personagem":
            if not usuario_logado: return self._redirect("/login")
            n, f_val = parametros.get("nome", [""])[0], parametros.get("funcao", ["dano"])[0].lower()
            try: niv = float(parametros.get("nivel", ["1"])[0])
            except: niv = 1.0
            PersonagemDAO().create(Personagem(0, n, niv, usuario_logado['id'], f_val))
            self._redirect("/personagens")

        elif caminho == "/atualizar_personagem":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(parametros.get("id", [0])[0])
            n, f_val = parametros.get("nome", [""])[0], parametros.get("funcao", ["dano"])[0].lower()
            niv = float(parametros.get("nivel", [1.0])[0])
            PersonagemDAO().update(id_p, n, niv, usuario_logado['id'], f_val)
            self._redirect("/personagens")

        elif caminho == "/processar_criacao_grupo":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(parametros.get("id_p", [0])[0])
            dao_p = PersonagemDAO()
            p = dao_p.read(id_p)
            if not p or p.id_conta != usuario_logado['id']:
                return self._render_mensagem("Acesso Negado", "Escolha um personagem da sua conta para criar o grupo.", "/criar_grupo_web", "Voltar")
            id_g = dao_grupo.criar_grupo_automatico(usuario_logado['id'], id_p, dao_p)
            if id_g:
                self._redirect(f"/detalhes_grupo?id={id_g}")
            else:
                self._render_mensagem("Erro ao criar grupo", "Personagem inválido para liderança do grupo.", "/grupos", "Voltar")

        elif caminho == "/entrar_no_grupo_final":
            if not usuario_logado: return self._redirect("/login")

            id_g = int(urllib.parse.parse_qs(url_parseada.query).get('id_g', [0])[0])
            id_p = int(parametros.get("id_p", [0])[0])
            dao_p = PersonagemDAO()

            # Garante que o personagem escolhido pertence ao usuário logado
            p = dao_p.read(id_p)
            if not p or p.id_conta != usuario_logado['id']:
                return self._render_mensagem("Acesso Negado", "Você só pode entrar no grupo com personagens da sua conta.", "/grupos", "Voltar")

            # Validação da regra 1 Tanque / 1 Suporte / 3 Danos
            if dao_grupo.adicionar_ao_grupo(id_g, usuario_logado['id'], id_p, dao_p):
                self._redirect(f"/detalhes_grupo?id={id_g}")
            else:
                self._render_mensagem("Erro de Composição!", "O grupo não pode aceitar este personagem (limite de função ou conta já presente).", "/grupos", "Voltar")

        elif caminho == "/excluir_conta":
            if not usuario_logado: return self._redirect("/login")
            ContaDAO().delete(usuario_logado['id'])
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()

        elif caminho == "/atualizar_conta":
            if not usuario_logado: return self._redirect("/login")
            email = parametros.get("email", [""])[0]
            data = parametros.get("data", [""])[0]
            dao = ContaDAO()
            conta = dao.read(usuario_logado['id'])
            if conta:
                conta_atualizada = Conta(conta.id, conta.usuario, email, data)
                dao.update(conta.id, conta_atualizada)
            self._redirect("/config_conta")

        elif caminho == "/salvar_bairro":
            if not usuario_logado: return self._redirect("/login")
            nome = parametros.get("nome", [""])[0].strip()
            try:
                id_dono = int(parametros.get("id_dono", [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Erro", "Selecione um personagem dono válido.", "/criar_bairro", "Voltar")
            if not nome:
                return self._render_mensagem("Erro", "Informe o nome do bairro.", "/criar_bairro", "Voltar")
            dao_p = PersonagemDAO()
            if not dao_p.read_by_id_and_conta(id_dono, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "O dono deve ser um personagem da sua conta.", "/criar_bairro", "Voltar")
            BairroDAO().create(Bairro(0, nome, id_dono))
            self._redirect("/bairros")

        elif caminho == "/atualizar_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_b = int(parametros.get("id", [0])[0])
                id_dono = int(parametros.get("id_dono", [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Erro", "Dados inválidos para atualização.", "/bairros", "Voltar")
            nome = parametros.get("nome", [""])[0].strip()
            if not nome:
                return self._render_mensagem("Erro", "Informe o nome do bairro.", f"/editar_bairro?id={id_b}", "Voltar")
            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_b)
            if not bairro or not self._bairro_pertence_conta(bairro, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "Você só pode editar bairros dos seus personagens.", "/bairros", "Voltar")
            dao_p = PersonagemDAO()
            if not dao_p.read_by_id_and_conta(id_dono, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "O novo dono deve ser um personagem da sua conta.", f"/editar_bairro?id={id_b}", "Voltar")
            if dao_bairro.update(id_b, nome, id_dono):
                self._redirect("/bairros")
            else:
                self._render_mensagem("Erro", "Não foi possível atualizar o bairro.", "/bairros", "Voltar")

        elif caminho == "/adicionar_personagem_bairro":
            if not usuario_logado: return self._redirect("/login")
            try:
                id_bairro = int(urllib.parse.parse_qs(url_parseada.query).get('id_bairro', [0])[0])
                id_p = int(parametros.get("id_p", [0])[0])
            except (ValueError, TypeError):
                return self._render_mensagem("Erro", "Dados inválidos.", "/bairros", "Voltar")

            dao_bairro = BairroDAO()
            bairro = dao_bairro.read(id_bairro)
            if not bairro or not self._bairro_pertence_conta(bairro, usuario_logado['id']):
                return self._render_mensagem("Acesso negado", "Você só pode adicionar personagens em bairros dos seus personagens.", f"/bairros_personagens?id={id_bairro}", "Voltar")

            # Valida que o personagem existe (qualquer conta)
            if not PersonagemDAO().read(id_p):
                return self._render_mensagem("Personagem inválido", "Personagem não encontrado.", f"/bairros_personagens?id={id_bairro}", "Voltar")

            if dao_bairro.adicionar_personagem(id_bairro, id_p):
                self._redirect(f"/bairros_personagens?id={id_bairro}")
            else:
                self._render_mensagem("Erro", "Não foi possível adicionar (talvez já esteja no bairro).", f"/bairros_personagens?id={id_bairro}", "Voltar")

    # --- AUXILIARES ---
    
    def _redirect(self, url):
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()

    def _render_mensagem(self, tit, msg, link, txt):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(self._render_template('mensagem.html', {'titulo': tit, 'mensagem': msg, 'link': link, 'link_texto': txt}).encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer): pass

if __name__ == "__main__":
    server = ThreadedHTTPServer((HOST, PORT), Servidor)
    print(f"World of RPGcraft (WEB) Online em http://{HOST}:{PORT}")
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()