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

HOST = "localhost"
PORT = 8000

# Instância global para persistência em memória durante a sessão
dao_grupo = GrupoTempDAO()

class Servidor(BaseHTTPRequestHandler):
    
    # --- UTILITÁRIOS ---
    
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
                        linhas_html += f"<tr><td>{p[0]}</td><td>{p[1]}</td><td>{p[2]}</td><td>{p[3]}</td>"
                        linhas_html += f"<td><a href='/editar_personagem?id={p[0]}' class='wow-link'>✏️ Editar</a> "
                        linhas_html += f"<a href='/excluir_personagem?id={p[0]}' class='wow-link wow-link-danger' onclick='return confirm(\"Excluir?\");'>🗑️ Excluir</a></td></tr>"
        return linhas_html

    # --- ROTAS GET ---

    def do_GET(self):
        usuario_logado = self._get_usuario_logado()
        url_parseada = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url_parseada.query)

        # Arquivos Estáticos e Imagens
        if self.path.startswith(("/static/", "/imagens/")):
            folder = "static" if "/static/" in self.path else "imagens"
            caminho = os.path.join("templates", folder, self.path.split(f"/{folder}/")[-1])
            if os.path.isfile(caminho):
                self.send_response(200)
                self.send_header("Content-type", mimetypes.guess_type(caminho)[0] or "application/octet-stream")
                self.end_headers()
                with open(caminho, "rb") as f: self.wfile.write(f.read())
            else: self.send_error(404)
            return

        # Roteamento
        if self.path == "/":
            self.send_response(200)
            self.end_headers()
            html = self._render_template('home_logado.html', {'usuario': usuario_logado['usuario']}) if usuario_logado else self._render_template('home.html')
            self.wfile.write(html.encode())

        elif self.path == "/personagens":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('personagens.html', {
                'usuario': usuario_logado['usuario'], 
                'personagens': self._gerar_linhas_personagens(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        # --- SISTEMA DE GRUPOS (FASE 2) ---
        
        elif self.path == "/grupos":
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
            
            html = self._render_template('grupos.html', {
                'usuario': usuario_logado['usuario'], 
                'lista_grupos': lista_html or "<p>Nenhum grupo ativo no momento.</p>"
            })
            self.wfile.write(html.encode())

        elif self.path.startswith("/detalhes_grupo"):
            if not usuario_logado: return self._redirect("/login")
            id_g = int(params.get('id', [0])[0])
            membros = dao_grupo.listar_membros_do_grupo(id_g)
            
            linhas = ""
            dao_p = PersonagemDAO()
            for m in membros:
                p = dao_p.read(m.id_personagem) # Busca via Hash PK
                if p:
                    f_str = p.funcao.decode().strip('\x00')
                    n_str = p.nome.decode().strip('\x00')
                    linhas += f"<tr><td>{m.id_conta}</td><td>{m.id_personagem}</td><td>{n_str}</td><td>{f_str}</td></tr>"
            
            self.send_response(200)
            self.end_headers()
            html = self._render_template('detalhes_grupo.html', {'id_grupo': id_g, 'linhas_membros': linhas})
            self.wfile.write(html.encode())

        elif self.path.startswith("/selecionar_personagem_grupo"):
            if not usuario_logado: return self._redirect("/login")
            id_g = int(params.get('id', [0])[0])
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_grupo_selecao.html', {
                'usuario': usuario_logado['usuario'],
                'id_grupo': id_g,
                'personagens': self._gerar_linhas_personagens(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        elif self.path.startswith("/entrar_no_grupo_final"):
            if not usuario_logado: return self._redirect("/login")
            id_g = int(params.get('id_g', [0])[0])
            id_p = int(params.get('id_p', [0])[0])
            
            dao_p = PersonagemDAO()
            # A regra 1 Tanque / 1 Suporte / 3 Danos é validada aqui
            if dao_grupo.adicionar_ao_grupo(id_g, usuario_logado['id'], id_p, dao_p):
                self._redirect(f"/detalhes_grupo?id={id_g}")
            else:
                self._render_mensagem("Erro de Composição!", "O grupo não pode aceitar este personagem (Limite de função atingido ou você já está no grupo).", "/grupos", "Voltar")

        elif self.path == "/criar_grupo_web":
            if not usuario_logado: return self._redirect("/login")
            self.send_response(200)
            self.end_headers()
            html = self._render_template('criar_grupo_selecao.html', {
                'usuario': usuario_logado['usuario'],
                'id_grupo': 0, # Indica que é criação
                'personagens': self._gerar_linhas_personagens(usuario_logado['id'])
            })
            self.wfile.write(html.encode())

        # Rotas de Cadastro/Login
        elif self.path == "/criar_conta":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._render_template('criar_conta.html').encode())

        elif self.path == "/login":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self._render_template('login.html').encode())

        elif self.path == "/logout":
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.send_header('Set-Cookie', 'usuario=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()

        elif self.path.startswith("/excluir_personagem"):
            if not usuario_logado: return self._redirect("/login")
            id_p = int(params.get('id', [0])[0])
            dao = PersonagemDAO()
            p = dao.read(id_p)
            if p and p.id_conta == usuario_logado['id']:
                dao.delete(id_p)
            self._redirect("/personagens")

        elif self.path.startswith("/editar_personagem"):
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

        else: self.send_error(404)

    # --- ROTAS POST ---

    def do_POST(self):
        usuario_logado = self._get_usuario_logado()
        tamanho = int(self.headers['Content-Length'])
        parametros = urllib.parse.parse_qs(self.rfile.read(tamanho).decode())

        if self.path == "/salvar_conta":
            u, e, d = parametros.get("usuario", [""])[0], parametros.get("email", [""])[0], parametros.get("data", [""])[0]
            dao = ContaDAO()
            if dao.read_por_usuario(u): return self._render_mensagem("Erro!", "Nome de usuário já existe.", "/criar_conta", "Voltar")
            dao.create(Conta(0, u, e, d))
            self._render_mensagem("Sucesso!", f"Conta de {u} criada!", "/", "Ir para início")

        elif self.path == "/autenticar":
            u = parametros.get("usuario", [""])[0]
            conta = ContaDAO().read_por_usuario(u)
            if conta and conta.lapide == b' ':
                self.send_response(302)
                self.send_header('Location', '/personagens')
                self._set_cookie('id_conta', str(conta.id))
                self._set_cookie('usuario', conta.usuario)
                self.end_headers()
            else: self._render_mensagem("Acesso Negado!", "Usuário não encontrado ou banido.", "/login", "Tentar novamente")

        elif self.path == "/salvar_personagem":
            if not usuario_logado: return self._redirect("/login")
            n, f_val = parametros.get("nome", [""])[0], parametros.get("funcao", ["dano"])[0].lower()
            try: niv = float(parametros.get("nivel", ["1"])[0])
            except: niv = 1.0
            PersonagemDAO().create(Personagem(0, n, niv, usuario_logado['id'], f_val))
            self._redirect("/personagens")

        elif self.path == "/atualizar_personagem":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(parametros.get("id", [0])[0])
            n, f_val = parametros.get("nome", [""])[0], parametros.get("funcao", ["dano"])[0].lower()
            niv = float(parametros.get("nivel", [1.0])[0])
            PersonagemDAO().update(id_p, n, niv, usuario_logado['id'], f_val)
            self._redirect("/personagens")

        elif self.path == "/processar_criacao_grupo":
            if not usuario_logado: return self._redirect("/login")
            id_p = int(parametros.get("id_p", [0])[0])
            dao_p = PersonagemDAO()
            id_g = dao_grupo.criar_grupo_automatico(usuario_logado['id'], id_p, dao_p)
            self._redirect(f"/detalhes_grupo?id={id_g}")

        elif self.path == "/excluir_conta":
            if not usuario_logado: return self._redirect("/login")
            # Exclusão lógica indexada
            ContaDAO().delete(usuario_logado['id'])
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()

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