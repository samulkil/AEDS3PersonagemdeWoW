from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import os
import re
import mimetypes
from dao.ContaDAO import ContaDAO
from model.Conta import Conta
from dao.PersonagemDAO import PersonagemDAO
from model.Personagem import Personagem
import socketserver

HOST = "localhost"
PORT = 8000

class Servidor(BaseHTTPRequestHandler):
    
    #Renderiza o template HTML
    def _render_template(self, nome_arquivo, contexto=None):
        
        if contexto is None:
            contexto = {}
        
        # Lê o template principal
        template_path = f'templates/{nome_arquivo}'
        
        if not os.path.exists(template_path):
            return f"<h1>Erro: Template {nome_arquivo} não encontrado</h1>"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # Processa herança ({% extends "base.html" %})
        extends_match = re.search(r'{%\s*extends\s+"([^"]+)"\s*%}', conteudo)
        
        if extends_match:
            base_template = extends_match.group(1)
            
            # Extrai os blocos do template filho
            blocos = {}
            padrao_bloco = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
            
            for match in re.finditer(padrao_bloco, conteudo, re.DOTALL):
                nome_bloco = match.group(1)
                conteudo_bloco = match.group(2)
                blocos[nome_bloco] = conteudo_bloco
            
            # Carrega o template base
            with open(f'templates/{base_template}', 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Substitui os blocos no template base
            for nome_bloco, conteudo_bloco in blocos.items():
                padrao = r'{%\s*block\s+' + nome_bloco + r'\s*%}.*?{%\s*endblock\s*%}'
                conteudo = re.sub(padrao, conteudo_bloco, conteudo, flags=re.DOTALL)
        
        # Processa includes ({% include "arquivo.html" %})
        def processa_include(match):
            include_file = match.group(1)
            try:
                with open(f'templates/{include_file}', 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return f"<!-- Erro ao incluir: {include_file} -->"
        
        conteudo = re.sub(r'{%\s*include\s+"([^"]+)"\s*%}', processa_include, conteudo)
        
        # Substitui variáveis ({{variavel}})
        for chave, valor in contexto.items():
            # Suporte a safe filter: {{variavel|safe}}
            padrao_safe = r'{{\s*' + chave + r'\s*\|\s*safe\s*}}'
            if re.search(padrao_safe, conteudo):
                conteudo = re.sub(padrao_safe, str(valor), conteudo)
            else:
                # Escapa HTML por padrão
                valor_escapado = str(valor).replace('<', '&lt;').replace('>', '&gt;')
                padrao = r'{{\s*' + chave + r'\s*}}'
                conteudo = re.sub(padrao, valor_escapado, conteudo)
        
        # Remove blocos não processados (limpeza)
        conteudo = re.sub(r'{%\s*block\s+\w+\s*%}.*?{%\s*endblock\s*%}', '', conteudo, flags=re.DOTALL)
        
        # Remove tags de template restantes
        conteudo = re.sub(r'{%[^%]*%}', '', conteudo)
        
        return conteudo
    
    
    # Pega Seta um cookie Simples
    def _set_cookie(self, nome, valor):

        self.send_header('Set-Cookie', f'{nome}={valor}; Path=/; HttpOnly')
            
    # Recupera os Cookies        
    def _get_cookie(self, nome):
    
        if 'Cookie' in self.headers:
            cookies = self.headers['Cookie'].split('; ')
            for cookie in cookies:
                if '=' in cookie:
                    chave, valor = cookie.split('=', 1)
                    if chave == nome:
                        return valor
        return None
    

    # Verifica se tem usuário logado e retorna seus dados
    def _get_usuario_logado(self):
       
        id_conta = self._get_cookie('id_conta')
        usuario = self._get_cookie('usuario')
        
        if id_conta and usuario:
            dao = ContaDAO()
            conta = dao.read(int(id_conta))
            if conta and conta.lapide == b' ':
                return {'id': int(id_conta), 'usuario': usuario}
        return None
    
    #  Gera as linhas da tabela de personagens
    def _gerar_linhas_personagens(self, id_conta):
        
        dao = PersonagemDAO()
        
        import io
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        dao.listar_por_conta(id_conta)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        linhas_html = ""
        
        if output.strip():
            linhas = output.strip().split('\n')
            
            for linha in linhas:
                if '|' in linha:
                    partes = [p.strip() for p in linha.split('|')]
                    if len(partes) >= 4:
                        linhas_html += "<tr>"
                        linhas_html += f"<td>{partes[0]}</td>"
                        linhas_html += f"<td>{partes[1]}</td>"
                        linhas_html += f"<td>{partes[2]}</td>"
                        linhas_html += f"<td>{partes[3]}</td>"
                        linhas_html += "<td>"
                        linhas_html += f"<a href='/editar_personagem?id={partes[0]}' class='wow-link'>✏️ Editar</a> "
                        linhas_html += f"<a href='/excluir_personagem?id={partes[0]}' class='wow-link wow-link-danger' onclick='return confirm(\"Tem certeza que deseja excluir este personagem?\");'>🗑️ Excluir</a>"
                        linhas_html += "</td>"
                        linhas_html += "</tr>"
        
        return linhas_html
    
    def do_GET(self):
        usuario_logado = self._get_usuario_logado()

        # Rota: Arquivos estáticos (CSS/JS)
        if self.path.startswith("/static/"):
            caminho_relativo = self.path[len("/static/"):]
            caminho_seguro = os.path.normpath(caminho_relativo).replace("\\", "/")

            if ".." in caminho_seguro:
                self.send_response(403)
                self.end_headers()
                return

            caminho_arquivo = os.path.join("templates", "static", caminho_seguro)
            if not os.path.isfile(caminho_arquivo):
                self.send_response(404)
                self.end_headers()
                return

            tipo, _ = mimetypes.guess_type(caminho_arquivo)
            if not tipo:
                tipo = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-type", tipo)
            self.end_headers()

            with open(caminho_arquivo, "rb") as f:
                self.wfile.write(f.read())
            return

        # Rota: Arquivos de imagem (fundo/recursos visuais)
        if self.path.startswith("/imagens/"):
            caminho_relativo = self.path[len("/imagens/"):]
            caminho_seguro = os.path.normpath(caminho_relativo).replace("\\", "/")

            if ".." in caminho_seguro:
                self.send_response(403)
                self.end_headers()
                return

            caminho_arquivo = os.path.join("templates", "imagens", caminho_seguro)
            if not os.path.isfile(caminho_arquivo):
                self.send_response(404)
                self.end_headers()
                return

            tipo, _ = mimetypes.guess_type(caminho_arquivo)
            if not tipo:
                tipo = "application/octet-stream"

            self.send_response(200)
            self.send_header("Content-type", tipo)
            self.end_headers()

            with open(caminho_arquivo, "rb") as f:
                self.wfile.write(f.read())
            return
        
        # Rota: Home
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            if usuario_logado:
                contexto = {
                    'usuario': usuario_logado['usuario'],
                    'id': usuario_logado['id']
                }
                html = self._render_template('home_logado.html', contexto)
            else:
                html = self._render_template('home.html')
            
            self.wfile.write(html.encode())
        
        # Rota: Criar Conta
        elif self.path == "/criar_conta":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = self._render_template('criar_conta.html')
            self.wfile.write(html.encode())
        
        # Rota: Login
        elif self.path == "/login":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            if usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/personagens')
                self.end_headers()
            else:
                html = self._render_template('login.html')
                self.wfile.write(html.encode())
        
        # Rota: Logout
        elif self.path == "/logout":
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.send_header('Set-Cookie', 'usuario=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()
        
        # Rota: Meus Personagens
        elif self.path == "/personagens":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            linhas_tabela = self._gerar_linhas_personagens(usuario_logado['id'])
            
            contexto = {
                'usuario': usuario_logado['usuario'],
                'personagens': linhas_tabela
            }
            
            html = self._render_template('personagens.html', contexto)
            self.wfile.write(html.encode())
        
        # Rota: Criar Personagem
        elif self.path == "/criar_personagem":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            contexto = {
                'usuario': usuario_logado['usuario']
            }
            
            html = self._render_template('criar_personagem.html', contexto)
            self.wfile.write(html.encode())
        
        # Rota: Configurações da Conta
        elif self.path == "/config_conta":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            dao = ContaDAO()
            conta = dao.read(usuario_logado['id'])
            
            contexto = {
                'id': conta.id,
                'usuario': conta.usuario,
                'email': conta.email,
                'data': conta.data
            }
            
            html = self._render_template('config_conta.html', contexto)
            self.wfile.write(html.encode())
        
        # Rota: Confirmar exclusão da conta
        elif self.path == "/confirmar_excluir_conta":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            contexto = {
                'usuario': usuario_logado['usuario'],
                'id': usuario_logado['id']
            }
            
            html = self._render_template('confirmar_excluir_conta.html', contexto)
            self.wfile.write(html.encode())
        
        # Rota: Excluir Personagem
        elif self.path.startswith("/excluir_personagem"):
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            id_personagem = int(params.get('id', [0])[0])
            
            if id_personagem:
                dao = PersonagemDAO()
                personagem = dao.read(id_personagem)
                
                if personagem and personagem.id_conta == usuario_logado['id']:
                    dao.delete(id_personagem)
            
            self.send_response(302)
            self.send_header('Location', '/personagens')
            self.end_headers()
        
        # Rota: Editar Personagem
        elif self.path.startswith("/editar_personagem"):
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            id_personagem = int(params.get('id', [0])[0])
            
            dao = PersonagemDAO()
            personagem = dao.read(id_personagem)
            
            if not personagem or personagem.id_conta != usuario_logado['id']:
                self.send_response(403)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Acesso negado!</h1>")
                return
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            nome_personagem = personagem.nome.decode('utf-8').strip('\x00') if isinstance(personagem.nome, bytes) else personagem.nome
            funcao_personagem = personagem.funcao.decode('utf-8').strip('\x00') if isinstance(personagem.funcao, bytes) else personagem.funcao
            
            contexto = {
                'id': personagem.id,
                'nome': nome_personagem,
                'nivel': personagem.nivel,
                'usuario': usuario_logado['usuario'],
                'selected_dano': 'selected' if funcao_personagem == 'dano' else '',
                'selected_tanque': 'selected' if funcao_personagem == 'tanque' else '',
                'selected_suporte': 'selected' if funcao_personagem == 'suporte' else ''
            }
            
            html = self._render_template('editar_personagem.html', contexto)
            self.wfile.write(html.encode())
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 - Pagina nao encontrada</h1>")
    
    def do_POST(self):
        usuario_logado = self._get_usuario_logado()
        
        # Rota: Salvar Conta
        if self.path == "/salvar_conta":
            tamanho = int(self.headers['Content-Length'])
            dados = self.rfile.read(tamanho).decode()
            parametros = urllib.parse.parse_qs(dados)
            
            usuario = parametros.get("usuario", [""])[0]
            email = parametros.get("email", [""])[0]
            data = parametros.get("data", [""])[0]
            
            if not usuario or not email or not data:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Todos os campos sao obrigatorios!</h1>")
                return
            
            dao = ContaDAO()
            existente = dao.read_por_usuario(usuario)
            
            if existente:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                html = self._render_template('mensagem.html', {
                    'titulo': 'Erro!',
                    'mensagem': 'Nome de usuário já existe. Escolha outro.',
                    'link': '/criar_conta',
                    'link_texto': 'Voltar'
                })
                self.wfile.write(html.encode())
                return
            
            conta = Conta(0, usuario, email, data)
            dao.create(conta)
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = self._render_template('mensagem.html', {
                'titulo': 'Conta criada com sucesso!',
                'mensagem': f'Bem-vindo, {usuario}! Sua jornada começa agora.',
                'link': '/',
                'link_texto': 'Ir para o início'
            })
            self.wfile.write(html.encode())
        
        # Rota: Autenticar (Login)
        elif self.path == "/autenticar":
            tamanho = int(self.headers['Content-Length'])
            dados = self.rfile.read(tamanho).decode()
            parametros = urllib.parse.parse_qs(dados)
            
            usuario = parametros.get("usuario", [""])[0]
            
            if not usuario:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Usuario obrigatorio!</h1>")
                return
            
            dao = ContaDAO()
            conta = dao.read_por_usuario(usuario)
            
            if conta and conta.lapide == b' ':
                self.send_response(302)
                self.send_header('Location', '/personagens')
                self._set_cookie('id_conta', str(conta.id))
                self._set_cookie('usuario', conta.usuario)
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                
                html = self._render_template('mensagem.html', {
                    'titulo': 'Login falhou!',
                    'mensagem': 'Usuário não encontrado ou conta desativada.',
                    'link': '/login',
                    'link_texto': 'Tentar novamente'
                })
                self.wfile.write(html.encode())
        
        # Rota: Salvar Personagem
        elif self.path == "/salvar_personagem":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            tamanho = int(self.headers['Content-Length'])
            dados = self.rfile.read(tamanho).decode()
            parametros = urllib.parse.parse_qs(dados)
            
            nome = parametros.get("nome", [""])[0]
            funcao = parametros.get("funcao", ["dano"])[0].lower()
            try:
                nivel = float(parametros.get("nivel", ["0"])[0])
            except ValueError:
                nivel = 1.0
            
            if not nome:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Nome do personagem obrigatorio!</h1>")
                return

            funcoes_validas = {"dano", "tanque", "suporte"}
            if funcao not in funcoes_validas:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Funcao invalida! Escolha entre dano, tanque ou suporte.</h1>")
                return
            
            dao = PersonagemDAO()
            personagem = Personagem(0, nome, nivel, usuario_logado['id'], funcao)
            dao.create(personagem)
            
            self.send_response(302)
            self.send_header('Location', '/personagens')
            self.end_headers()
        
        # Rota: Atualizar Personagem
        elif self.path == "/atualizar_personagem":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            tamanho = int(self.headers['Content-Length'])
            dados = self.rfile.read(tamanho).decode()
            parametros = urllib.parse.parse_qs(dados)
            
            id_personagem = int(parametros.get("id", [0])[0])
            nome = parametros.get("nome", [""])[0]
            nivel = float(parametros.get("nivel", [1.0])[0])
            funcao = parametros.get("funcao", [""])[0].lower()
            
            dao = PersonagemDAO()
            personagem = dao.read(id_personagem)
            
            if personagem and personagem.id_conta == usuario_logado['id']:
                if not funcao:
                    funcao = personagem.funcao.decode('utf-8').strip('\x00')

                funcoes_validas = {"dano", "tanque", "suporte"}
                if funcao in funcoes_validas:
                    dao.update(id_personagem, nome, nivel, usuario_logado['id'], funcao)
            
            self.send_response(302)
            self.send_header('Location', '/personagens')
            self.end_headers()
        
        # Rota: Atualizar Conta
        elif self.path == "/atualizar_conta":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            tamanho = int(self.headers['Content-Length'])
            dados = self.rfile.read(tamanho).decode()
            parametros = urllib.parse.parse_qs(dados)
            
            email = parametros.get("email", [""])[0]
            data = parametros.get("data", [""])[0]
            
            dao = ContaDAO()
            conta = dao.read(usuario_logado['id'])
            
            if conta:
                conta_atualizada = Conta(conta.id, conta.usuario, email, data)
                dao.update(conta.id, conta_atualizada)
            
            self.send_response(302)
            self.send_header('Location', '/config_conta')
            self.end_headers()
        
        # Rota: Excluir Conta
        elif self.path == "/excluir_conta":
            if not usuario_logado:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
            
            dao_conta = ContaDAO()
            dao_perso = PersonagemDAO()
            
            import io
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            dao_perso.listar_por_conta(usuario_logado['id'])
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            import re
            ids_personagens = re.findall(r'^(\d+)', output, re.MULTILINE)
            
            for id_str in ids_personagens:
                dao_perso.delete(int(id_str))
            
            dao_conta.delete(usuario_logado['id'])
            
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'id_conta=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.send_header('Set-Cookie', 'usuario=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    pass

if __name__ == "__main__":
    os.makedirs('templates', exist_ok=True)
    
    server = ThreadedHTTPServer((HOST, PORT), Servidor)
    print(f" World of RPGcraft rodando em http://{HOST}:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Servidor encerrado!")
        server.server_close()