from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import os
import re
import mimetypes
import socketserver

from dao.ContaDAO import ContaDAO
from model.Conta import Conta
from dao.PersonagemDAO import PersonagemDAO
from model.Personagem import Personagem
from dao.GrupoTempDAO import GrupoTempDAO

HOST = "localhost"
PORT = 8001

dao_grupo = GrupoTempDAO()

class Servidor(BaseHTTPRequestHandler):
    
    
    def _render_template(self, nome_arquivo, contexto=None):
        if contexto is None: contexto = {}
        template_path = f'templates/{nome_arquivo}'
        
        if not os.path.exists(template_path):
            return f"<h1>Erro: Template {nome_arquivo} nÃ£o encontrado</h1>"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
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
        
        conteudo = re.sub(r'{%\s*include\s+"([^"]+)"\s*%}', 
                         lambda m: open(f"templates/{m.group(1)}", 'r', encoding='utf-8').read(), 
                         conteudo)
        
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
        """Usa o relacionamento 1:N via Hash ExtensÃ­vel para listar personagens."""
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
                if '|' in linha:
                    p = [part.strip() for part in linha.split('|')]
                    if len(p) >= 4:
                        linhas_html += f"<tr><td>{p[0]}</td><td>{p[1]}</td><td>{p[2]}</td><td>{p[3]}</td>"
                        linhas_html += f"<td><a href='/editar_personagem?id={p[0]}' class='wow-link'>âœï¸ Editar</a> "
                        linhas_html += f"<a href='/excluir_personagem?id={p[0]}' class='wow-link wow-link-danger' onclick='return confirm(\"Excluir?\");'>ðŸ—‘ï¸ Excluir</a></td></tr>"
        return linhas_html

    def _gerar_visualizacao_bplus_id(self):
        """Monta uma visualizaÃ§Ã£o textual da Ãrvore B+ (Ã­ndice por ID)."""
        try:
            dao = PersonagemDAO()
            arvore = dao.arvore_id
            raiz = arvore._ler_raiz()
            if raiz == -1:
                return "<p class='wow-note'>Ãrvore B+ vazia.</p>"

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
                prox = f" | prox: {no.proximo}" if no.eh_folha else ""
                cartao = f"<div class='wow-card' style='min-width: 220px; margin: 6px;'><strong>{tipo}</strong><br>off: {offset}<br>chaves: [{chaves}]{prox}</div>"
                niveis.setdefault(nivel, []).append(cartao)

                if not no.eh_folha:
                    for filho in no.ponteiros:
                        if filho not in (None, -1, 0):
                            fila.append((filho, nivel + 1))

            html.append("<div style='display:flex; flex-direction:column; gap:10px;'>")
            for nivel in sorted(niveis.keys()):
                html.append(f"<div><div class='wow-note' style='margin-bottom:4px;'><strong>NÃ­vel {nivel}</strong></div>")
                html.append("<div style='display:flex; flex-wrap:wrap;'>")
                html.extend(niveis[nivel])
                html.append("</div></div>")
            html.append("</div>")

            no = arvore._ler_no(raiz)
            while not no.eh_folha and no.ponteiros:
                no = arvore._ler_no(no.ponteiros[0])

            folhas = []
            while no:
                folhas.append("[" + ", ".join(str(c) for c in no.chaves) + "]")
                if no.proximo in (-1, None):
                    break
                no = arvore._ler_no(no.proximo)

            if folhas:
                html.append("<div class='wow-card' style='margin-top:10px;'>")
                html.append("<div class='wow-note'><strong>Encadeamento das folhas:</strong> " + " â†’ ".join(folhas) + "</div>")
                html.append("</div>")

            return "".join(html)
        except Exception as e:
            return f"<p class='wow-note'>NÃ£o foi possÃ­vel renderizar a Ãrvore B+: {e}</p>"

    def _gerar_linhas_personagens_selecao_grupo(self, id_conta):
        """Gera linhas de seleÃ§Ã£o com radio pronto para criar/entrar em grupo."""
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

    def do_GET(self):
        usuario_logado = self._get_usuario_logado()
        url_parseada = urllib.parse.urlparse(self.path)
        caminho = url_parseada.path.rstrip('/') or '/'
        params = urllib.parse.parse_qs(url_parseada.query)

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

        elif caminho == "/arvore_bplus":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('arvore_bplus.html', {
                'usuario': usuario_logado['usuario'],
                'visualizacao_bplus': self._gerar_visualizacao_bplus_id()
            })
            self.wfile.write(html.encode())

        
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
                return self._render_mensagem("ID invÃ¡lido", "Informe um ID de grupo vÃ¡lido para ver os detalhes.", "/grupos", "Voltar")
            membros = dao_grupo.listar_membros_do_grupo(id_g)
            
            linhas = ""
            dao_p = PersonagemDAO()
            dao_c = ContaDAO()
            for m in membros:
                p = dao_p.read(m.id_personagem)
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
                'titulo_grupo': f"Juntar-se ao Grupo
                'form_action': f"/entrar_no_grupo_final?id_g={id_g}"
            })
            self.wfile.write(html.encode())

        elif caminho == "/entrar_no_grupo_final":
            if not usuario_logado: return self._redirect("/login")
            self._redirect("/grupos")

        elif caminho == "/criar_grupo_web":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_grupo_selecao.html', {
                'usuario': usuario_logado['usuario'],
                'id_grupo': 0,
                'personagens': self._gerar_linhas_personagens_selecao_grupo(usuario_logado['id']),
                'titulo_grupo': "Iniciar Nova Jornada",
                'form_action': "/processar_criacao_grupo"
            })
            self.wfile.write(html.encode())

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
                return self._render_mensagem("Conta nÃ£o encontrada", "NÃ£o foi possÃ­vel carregar suas configuraÃ§Ãµes.", "/personagens", "Voltar")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('config_conta.html', {
                'id': conta.id,
                'usuario': conta.usuario,
                'email': conta.email,
                'data': conta.data
            })
            self.wfile.write(html.encode())

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

    def do_POST(self):
        usuario_logado = self._get_usuario_logado()
        url_parseada = urllib.parse.urlparse(self.path)
        caminho = url_parseada.path.rstrip('/') or '/'
        
        tamanho = int(self.headers['Content-Length'])
        parametros = urllib.parse.parse_qs(self.rfile.read(tamanho).decode())

        if caminho == "/salvar_conta":
            u, e, d = parametros.get("usuario", [""])[0], parametros.get("email", [""])[0], parametros.get("data", [""])[0]
            dao = ContaDAO()
            if dao.read_por_usuario(u): return self._render_mensagem("Erro!", "Nome de usuÃ¡rio jÃ¡ existe.", "/criar_conta", "Voltar")
            dao.create(Conta(0, u, e, d))
            self._render_mensagem("Sucesso!", f"Conta de {u} criada!", "/", "Ir para inÃ­cio")

        elif caminho == "/autenticar":
            u = parametros.get("usuario", [""])[0]
            conta = ContaDAO().read_por_usuario(u)
            if conta and conta.lapide == b' ':
                self.send_response(302)
                self.send_header('Location', '/personagens')
                self._set_cookie('id_conta', str(conta.id))
                self._set_cookie('usuario', conta.usuario)
                self.end_headers()
            else: self._render_mensagem("Acesso Negado!", "UsuÃ¡rio nÃ£o encontrado.", "/login", "Tentar novamente")

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
                self._render_mensagem("Erro ao criar grupo", "Personagem invÃ¡lido para lideranÃ§a do grupo.", "/grupos", "Voltar")

        elif caminho == "/entrar_no_grupo_final":
            if not usuario_logado: return self._redirect("/login")

            id_g = int(urllib.parse.parse_qs(url_parseada.query).get('id_g', [0])[0])
            id_p = int(parametros.get("id_p", [0])[0])
            dao_p = PersonagemDAO()

            p = dao_p.read(id_p)
            if not p or p.id_conta != usuario_logado['id']:
                return self._render_mensagem("Acesso Negado", "VocÃª sÃ³ pode entrar no grupo com personagens da sua conta.", "/grupos", "Voltar")

            if dao_grupo.adicionar_ao_grupo(id_g, usuario_logado['id'], id_p, dao_p):
                self._redirect(f"/detalhes_grupo?id={id_g}")
            else:
                self._render_mensagem("Erro de ComposiÃ§Ã£o!", "O grupo nÃ£o pode aceitar este personagem (limite de funÃ§Ã£o ou conta jÃ¡ presente).", "/grupos", "Voltar")

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