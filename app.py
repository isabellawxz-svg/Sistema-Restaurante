# app.py
# Flask + SQLite: autenticação por sessão, papéis (admin, caixa, garçom), cardápio e comandas.

import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "altere-esta-chave-em-producao")
DB_PATH = "dados.db"

# pbkdf2: compatível com Python/hashlib sem scrypt (ex.: alguns builds antigos).
_HASH_METHOD = "pbkdf2:sha256"
FORMAS_PAGAMENTO = ("dinheiro", "pix", "cartao")
PAPEIS = ("admin", "caixa", "garcom")
MESA_STATUS = ("livre", "ocupada", "reservada")


def _auth_fail():
    if request.path.startswith("/api/"):
        return jsonify({"erro": "faça login"}), 401
    return redirect(url_for("login"))


def _forbid():
    if request.path.startswith("/api/"):
        return jsonify({"erro": "permissão negada"}), 403
    return redirect(url_for("login", negado=1))


def staff_required(*roles):
    """Exige login; se roles for informado, restringe a esses papéis."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return _auth_fail()
            if roles and session.get("role") not in roles:
                return _forbid()
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _ensure_legacy_pedidos_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pedidos'")
    if not cursor.fetchone():
        conn.close()
        return
    cursor.execute("PRAGMA table_info(pedidos)")
    cols = {row[1] for row in cursor.fetchall()}
    for sql in (
        "ALTER TABLE pedidos ADD COLUMN mesa TEXT NOT NULL DEFAULT ''" if "mesa" not in cols else None,
        "ALTER TABLE pedidos ADD COLUMN cliente_nome TEXT NOT NULL DEFAULT ''"
        if "cliente_nome" not in cols
        else None,
        "ALTER TABLE pedidos ADD COLUMN status TEXT NOT NULL DEFAULT 'recebido'" if "status" not in cols else None,
        "ALTER TABLE pedidos ADD COLUMN pagamento_status TEXT NOT NULL DEFAULT 'pendente'"
        if "pagamento_status" not in cols
        else None,
        "ALTER TABLE pedidos ADD COLUMN forma_pagamento TEXT" if "forma_pagamento" not in cols else None,
    ):
        if sql:
            cursor.execute(sql)
    conn.commit()
    conn.close()


def _migrate_pedidos_para_comandas(cursor):
    cursor.execute("SELECT COUNT(*) FROM comandas")
    if cursor.fetchone()[0] > 0:
        return
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pedidos'")
    if not cursor.fetchone():
        return
    cursor.execute("SELECT COUNT(*) FROM pedidos")
    if cursor.fetchone()[0] == 0:
        return
    cursor.execute(
        "SELECT id, criado_em, mesa, cliente_nome, pagamento_status, forma_pagamento FROM pedidos ORDER BY id"
    )
    for row in cursor.fetchall():
        old_id = row["id"]
        pag = row["pagamento_status"] or "pendente"
        fechada = pag == "pago"
        status = "fechada" if fechada else "aberta"
        fechada_em = row["criado_em"] if fechada else None
        cursor.execute(
            """
            INSERT INTO comandas (criado_em, mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["criado_em"],
                row["mesa"] or "",
                row["cliente_nome"] or "",
                status,
                pag,
                row["forma_pagamento"] if fechada else None,
                fechada_em,
            ),
        )
        novo_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO itens_comanda (id_comanda, id_item, quantidade)
            SELECT ?, id_item, quantidade FROM itens_pedido WHERE id_pedido = ?
            """,
            (novo_id, old_id),
        )


def _seed_usuario_admin(cursor):
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] > 0:
        return
    h = generate_password_hash("admin123", method=_HASH_METHOD)
    cursor.execute(
        """
        INSERT INTO usuarios (login, senha_hash, papel, nome_exibicao, ativo)
        VALUES ('admin', ?, 'admin', 'Administrador', 1)
        """,
        (h,),
    )


def _ensure_comandas_total_quitacao(cursor):
    cursor.execute("PRAGMA table_info(comandas)")
    cols = {r[1] for r in cursor.fetchall()}
    if "total_quitacao" not in cols:
        cursor.execute("ALTER TABLE comandas ADD COLUMN total_quitacao REAL")


def _ensure_insumos_compras_composicao(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            unidade TEXT NOT NULL DEFAULT 'un',
            estoque_atual REAL NOT NULL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor TEXT NOT NULL DEFAULT '',
            numero_nota TEXT NOT NULL DEFAULT '',
            data_nota TEXT NOT NULL DEFAULT '',
            observacao TEXT NOT NULL DEFAULT '',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_nota_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_nota INTEGER NOT NULL,
            id_insumo INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            valor_unitario REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (id_nota) REFERENCES notas_compra(id),
            FOREIGN KEY (id_insumo) REFERENCES insumos(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS composicao_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_item_cardapio INTEGER NOT NULL,
            id_insumo INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            UNIQUE (id_item_cardapio, id_insumo),
            FOREIGN KEY (id_item_cardapio) REFERENCES itens_cardapio(id),
            FOREIGN KEY (id_insumo) REFERENCES insumos(id)
        )
    """)


def _ensure_itens_cardapio_categoria(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_cardapio'")
    if not cursor.fetchone():
        return
    cursor.execute("PRAGMA table_info(itens_cardapio)")
    cols = {r[1] for r in cursor.fetchall()}
    if "categoria" not in cols:
        cursor.execute("ALTER TABLE itens_cardapio ADD COLUMN categoria TEXT NOT NULL DEFAULT ''")


def _ensure_insumos_estoque_minimo(cursor):
    cursor.execute("PRAGMA table_info(insumos)")
    cols = {r[1] for r in cursor.fetchall()}
    if "estoque_minimo" not in cols:
        cursor.execute("ALTER TABLE insumos ADD COLUMN estoque_minimo REAL NOT NULL DEFAULT 0")


def _ensure_mesas_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            capacidade INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT 'livre',
            id_comanda_ativa INTEGER,
            FOREIGN KEY (id_comanda_ativa) REFERENCES comandas(id)
        )
    """)
    cursor.execute("PRAGMA table_info(comandas)")
    cols = {r[1] for r in cursor.fetchall()}
    if "id_mesa" not in cols:
        cursor.execute("ALTER TABLE comandas ADD COLUMN id_mesa INTEGER REFERENCES mesas(id)")


def _seed_mesas(cursor):
    cursor.execute("SELECT COUNT(*) FROM mesas")
    if cursor.fetchone()[0] > 0:
        return
    for i in range(1, 13):
        cap = 4 if i <= 8 else 6
        cursor.execute(
            "INSERT INTO mesas (numero, capacidade, status) VALUES (?, ?, 'livre')",
            (str(i), cap),
        )


def _sync_comandas_abertas_com_mesas(cursor):
    """Vincula comandas abertas existentes às mesas pelo número (após migração)."""
    cursor.execute(
        """
        SELECT c.id, c.mesa FROM comandas c
        WHERE c.status = 'aberta' AND TRIM(COALESCE(c.mesa, '')) != ''
        """
    )
    for row in cursor.fetchall():
        cursor.execute(
            "SELECT id, status, id_comanda_ativa FROM mesas WHERE numero = ?",
            (row["mesa"].strip(),),
        )
        mesa = cursor.fetchone()
        if not mesa:
            continue
        if mesa["status"] == "ocupada" and mesa["id_comanda_ativa"] not in (None, row["id"]):
            continue
        cursor.execute("UPDATE comandas SET id_mesa = ? WHERE id = ?", (mesa["id"], row["id"]))
        cursor.execute(
            """
            UPDATE mesas SET status = 'ocupada', id_comanda_ativa = ?
            WHERE id = ? AND (status = 'livre' OR id_comanda_ativa = ? OR id_comanda_ativa IS NULL)
            """,
            (row["id"], mesa["id"], row["id"]),
        )


def _liberar_mesa_por_comanda(cursor, id_comanda):
    cursor.execute(
        """
        UPDATE mesas SET status = 'livre', id_comanda_ativa = NULL
        WHERE id_comanda_ativa = ?
        """,
        (id_comanda,),
    )


def _ocupar_mesa_para_comanda(cursor, id_mesa, id_comanda):
    cursor.execute(
        "SELECT id, numero, status, id_comanda_ativa FROM mesas WHERE id = ?",
        (id_mesa,),
    )
    mesa = cursor.fetchone()
    if not mesa:
        return "mesa não encontrada"
    if mesa["status"] == "reservada":
        return "mesa reservada — libere a reserva no admin antes de abrir comanda"
    if mesa["status"] == "ocupada" and mesa["id_comanda_ativa"] not in (None, id_comanda):
        return "mesa já está ocupada por outra comanda"
    cursor.execute(
        """
        UPDATE mesas SET status = 'ocupada', id_comanda_ativa = ?
        WHERE id = ?
        """,
        (id_comanda, id_mesa),
    )
    cursor.execute("UPDATE comandas SET id_mesa = ? WHERE id = ?", (id_mesa, id_comanda))
    return None


def ensure_schema():
    _ensure_legacy_pedidos_columns()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comandas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mesa TEXT NOT NULL DEFAULT '',
            cliente_nome TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'aberta',
            pagamento_status TEXT NOT NULL DEFAULT 'pendente',
            forma_pagamento TEXT,
            fechada_em TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_comanda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_comanda INTEGER NOT NULL,
            id_item INTEGER NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_comanda) REFERENCES comandas(id),
            FOREIGN KEY (id_item) REFERENCES itens_cardapio(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            papel TEXT NOT NULL,
            nome_exibicao TEXT NOT NULL DEFAULT '',
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_comandas_total_quitacao(cursor)
    _ensure_insumos_compras_composicao(cursor)
    _ensure_itens_cardapio_categoria(cursor)
    _ensure_insumos_estoque_minimo(cursor)
    _ensure_mesas_schema(cursor)
    _seed_mesas(cursor)
    conn.commit()
    _migrate_pedidos_para_comandas(cursor)
    _sync_comandas_abertas_com_mesas(cursor)
    _seed_usuario_admin(cursor)
    conn.commit()
    conn.close()


ensure_schema()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _total_itens(itens):
    return sum(i["quantidade"] * i["preco"] for i in itens)


def _pode_editar_itens(row):
    return row["status"] == "aberta" and row["pagamento_status"] == "pendente"


def _pode_excluir(row):
    return row["status"] == "aberta" and row["pagamento_status"] == "pendente"


def _montar_comanda(cursor, id_comanda, row):
    cursor.execute(
        """
        SELECT ic.id_item, ic.quantidade, c.nome, c.preco
        FROM itens_comanda ic
        JOIN itens_cardapio c ON c.id = ic.id_item
        WHERE ic.id_comanda = ?
        """,
        (id_comanda,),
    )
    itens = []
    for r in cursor.fetchall():
        itens.append(
            {
                "id_item": r["id_item"],
                "quantidade": r["quantidade"],
                "nome": r["nome"],
                "preco": r["preco"],
            }
        )
    total_calc = _total_itens(itens)
    tq = row["total_quitacao"] if "total_quitacao" in row.keys() and row["total_quitacao"] is not None else None
    if row["status"] == "fechada" and tq is not None:
        total_final = round(float(tq), 2)
    else:
        total_final = round(total_calc, 2)
    id_mesa = row["id_mesa"] if "id_mesa" in row.keys() else None
    return {
        "id": id_comanda,
        "criado_em": row["criado_em"],
        "mesa": row["mesa"] or "",
        "id_mesa": id_mesa,
        "cliente_nome": row["cliente_nome"] or "",
        "status": row["status"],
        "pagamento_status": row["pagamento_status"],
        "forma_pagamento": row["forma_pagamento"],
        "fechada_em": row["fechada_em"],
        "total": total_final,
        "total_quitacao": tq,
        "itens": itens,
        "pode_editar_itens": _pode_editar_itens(row),
        "pode_excluir": _pode_excluir(row),
    }


def _calcular_consumo_insumos_comanda(cursor, id_comanda):
    """Soma insumos necessários para baixa ao fechar a comanda (ficha técnica × quantidade vendida)."""
    cursor.execute(
        """
        SELECT ic.id_item, ic.quantidade AS qtd_prato
        FROM itens_comanda ic WHERE ic.id_comanda = ?
        """,
        (id_comanda,),
    )
    consumos = {}
    for linha in cursor.fetchall():
        id_item = linha["id_item"]
        qtd_prato = linha["qtd_prato"]
        cursor.execute(
            """
            SELECT id_insumo, quantidade FROM composicao_item WHERE id_item_cardapio = ?
            """,
            (id_item,),
        )
        for comp in cursor.fetchall():
            need = float(comp["quantidade"]) * int(qtd_prato)
            iid = comp["id_insumo"]
            consumos[iid] = consumos.get(iid, 0.0) + need
    return consumos


def _validar_e_baixar_estoque(cursor, consumos):
    """Garante estoque e baixa. Retorna mensagem de erro ou None."""
    for id_insumo, need in consumos.items():
        cursor.execute("SELECT nome, estoque_atual FROM insumos WHERE id = ?", (id_insumo,))
        r = cursor.fetchone()
        if not r:
            return "Receita referencia insumo inexistente (id %s)." % id_insumo
        disp = float(r["estoque_atual"])
        if disp + 1e-9 < need:
            return "Estoque insuficiente de «%s»: precisa de %.4f, há %.4f." % (r["nome"], need, disp)
    for id_insumo, need in consumos.items():
        cursor.execute(
            "UPDATE insumos SET estoque_atual = estoque_atual - ? WHERE id = ?",
            (need, id_insumo),
        )
    return None


def _usuario_publico(row):
    return {
        "id": row["id"],
        "login": row["login"],
        "papel": row["papel"],
        "nome_exibicao": row["nome_exibicao"] or "",
        "ativo": bool(row["ativo"]),
        "criado_em": row["criado_em"],
    }


def _count_admins_ativos(cursor, exceto_id=None):
    if exceto_id is None:
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE papel = 'admin' AND ativo = 1")
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM usuarios WHERE papel = 'admin' AND ativo = 1 AND id != ?",
            (exceto_id,),
        )
    return cursor.fetchone()[0]


# --- Autenticação e redirecionamento ---


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_visao"))
    if role == "caixa":
        return redirect(url_for("pagina_caixa"))
    if role == "garcom":
        return redirect(url_for("pagina_garcom"))
    session.clear()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("index"))
        negado = request.args.get("negado")
        return render_template("login.html", negado=bool(negado))
    dados = request.get_json(silent=True) or {}
    login_u = (dados.get("login") or "").strip().lower()
    senha = dados.get("senha") or ""
    if not login_u or not senha:
        return jsonify({"erro": "informe usuário e senha"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, login, senha_hash, papel, nome_exibicao, ativo FROM usuarios WHERE lower(login) = ?",
        (login_u,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row or not row["ativo"]:
        return jsonify({"erro": "usuário ou senha inválidos"}), 401
    if not check_password_hash(row["senha_hash"], senha):
        return jsonify({"erro": "usuário ou senha inválidos"}), 401
    session["user_id"] = row["id"]
    session["role"] = row["papel"]
    session["nome"] = (row["nome_exibicao"] or "").strip() or row["login"]
    dest = url_for("admin_visao")
    if row["papel"] == "caixa":
        dest = url_for("pagina_caixa")
    elif row["papel"] == "garcom":
        dest = url_for("pagina_garcom")
    return jsonify({"ok": True, "redirect": dest})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/garcom")
@staff_required("admin", "garcom")
def pagina_garcom():
    return render_template("garcom.html")


@app.route("/caixa")
@staff_required("admin", "caixa")
def pagina_caixa():
    return render_template("caixa.html")


@app.route("/admin")
@staff_required("admin")
def pagina_admin():
    return redirect(url_for("admin_visao"))


@app.route("/admin/visao")
@staff_required("admin")
def admin_visao():
    return render_template("admin/visao.html")


@app.route("/admin/cardapio")
@staff_required("admin")
def admin_cardapio():
    return render_template("admin/cardapio.html")


@app.route("/admin/usuarios")
@staff_required("admin")
def admin_usuarios():
    return render_template("admin/usuarios.html")


@app.route("/admin/insumos")
@staff_required("admin")
def admin_insumos():
    return render_template("admin/insumos.html")


@app.route("/admin/notas-compra")
@staff_required("admin")
def admin_notas_compra():
    return render_template("admin/notas_compra.html")


@app.route("/admin/receitas")
@staff_required("admin")
def admin_receitas():
    return render_template("admin/receitas.html")


@app.route("/admin/financeiro")
@staff_required("admin")
def admin_financeiro():
    return render_template("admin/financeiro.html")


@app.route("/admin/mesas")
@staff_required("admin")
def admin_mesas():
    return render_template("admin/mesas.html")


@app.route("/caixa/financeiro")
@staff_required("admin", "caixa")
def caixa_financeiro():
    return render_template("caixa_financeiro.html")


# --- API cardápio ---


@app.route("/api/cardapio", methods=["GET"])
@staff_required("admin", "caixa", "garcom")
def listar_cardapio():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nome, preco, COALESCE(categoria, '') AS categoria
        FROM itens_cardapio
        ORDER BY categoria, nome
        """
    )
    itens = [
        {
            "id": row["id"],
            "nome": row["nome"],
            "preco": row["preco"],
            "categoria": row["categoria"] or "",
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return jsonify(itens)


@app.route("/api/cardapio", methods=["POST"])
@staff_required("admin")
def cadastrar_item():
    dados = request.get_json()
    nome = dados.get("nome")
    preco = dados.get("preco")
    categoria = (dados.get("categoria") or "").strip()
    if not nome or preco is None:
        return jsonify({"erro": "nome e preco são obrigatórios"}), 400
    try:
        preco = float(preco)
    except (TypeError, ValueError):
        return jsonify({"erro": "preco deve ser um número"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO itens_cardapio (nome, preco, categoria) VALUES (?, ?, ?)",
        (nome.strip(), preco, categoria),
    )
    conn.commit()
    id_novo = cursor.lastrowid
    conn.close()
    return jsonify({"id": id_novo, "nome": nome.strip(), "preco": preco, "categoria": categoria}), 201


@app.route("/api/cardapio/<int:id_item>", methods=["PUT"])
@staff_required("admin")
def editar_item(id_item):
    dados = request.get_json() or {}
    nome = dados.get("nome")
    preco = dados.get("preco")
    categoria = dados.get("categoria")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM itens_cardapio WHERE id = ?", (id_item,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "item não encontrado"}), 404
    if nome is not None:
        cursor.execute("UPDATE itens_cardapio SET nome = ? WHERE id = ?", (nome.strip(), id_item))
    if preco is not None:
        try:
            preco = float(preco)
            cursor.execute("UPDATE itens_cardapio SET preco = ? WHERE id = ?", (preco, id_item))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"erro": "preco deve ser um número"}), 400
    if categoria is not None:
        cursor.execute(
            "UPDATE itens_cardapio SET categoria = ? WHERE id = ?",
            ((categoria or "").strip(), id_item),
        )
    conn.commit()
    cursor.execute(
        "SELECT id, nome, preco, COALESCE(categoria, '') AS categoria FROM itens_cardapio WHERE id = ?",
        (id_item,),
    )
    row = cursor.fetchone()
    conn.close()
    return jsonify(
        {
            "id": row["id"],
            "nome": row["nome"],
            "preco": row["preco"],
            "categoria": row["categoria"] or "",
        }
    )


@app.route("/api/cardapio/<int:id_item>", methods=["DELETE"])
@staff_required("admin")
def excluir_item(id_item):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM composicao_item WHERE id_item_cardapio = ?", (id_item,))
    cursor.execute("DELETE FROM itens_comanda WHERE id_item = ?", (id_item,))
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_pedido'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM itens_pedido WHERE id_item = ?", (id_item,))
    cursor.execute("DELETE FROM itens_cardapio WHERE id = ?", (id_item,))
    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return jsonify({"erro": "item não encontrado"}), 404
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "item excluído"}), 200


# --- API usuários (somente admin) ---


@app.route("/api/usuarios", methods=["GET"])
@staff_required("admin")
def listar_usuarios():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, login, papel, nome_exibicao, ativo, criado_em FROM usuarios ORDER BY login"
    )
    lista = [_usuario_publico(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(lista)


@app.route("/api/usuarios", methods=["POST"])
@staff_required("admin")
def criar_usuario():
    dados = request.get_json() or {}
    login_u = (dados.get("login") or "").strip().lower()
    senha = dados.get("senha") or ""
    papel = (dados.get("papel") or "").strip()
    nome_exibicao = (dados.get("nome_exibicao") or "").strip()
    if not login_u or len(login_u) < 2:
        return jsonify({"erro": "login inválido (mínimo 2 caracteres)"}), 400
    if len(senha) < 4:
        return jsonify({"erro": "senha muito curta (mínimo 4 caracteres)"}), 400
    if papel not in PAPEIS:
        return jsonify({"erro": "papel deve ser: admin, caixa ou garcom"}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (login, senha_hash, papel, nome_exibicao, ativo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (login_u, generate_password_hash(senha, method=_HASH_METHOD), papel, nome_exibicao),
        )
        conn.commit()
        uid = cursor.lastrowid
        cursor.execute(
            "SELECT id, login, papel, nome_exibicao, ativo, criado_em FROM usuarios WHERE id = ?", (uid,)
        )
        row = cursor.fetchone()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return jsonify({"erro": "login já existe"}), 409
    conn.close()
    return jsonify(_usuario_publico(row)), 201


@app.route("/api/usuarios/<int:id_usuario>", methods=["PUT"])
@staff_required("admin")
def atualizar_usuario(id_usuario):
    dados = request.get_json() or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, login, papel, nome_exibicao, ativo FROM usuarios WHERE id = ?", (id_usuario,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "usuário não encontrado"}), 404
    novo_papel = dados.get("papel", row["papel"])
    if novo_papel not in PAPEIS:
        conn.close()
        return jsonify({"erro": "papel inválido"}), 400
    novo_ativo = dados.get("ativo")
    if novo_ativo is not None:
        novo_ativo = 1 if novo_ativo else 0
    else:
        novo_ativo = row["ativo"]
    nome_exibicao = dados.get("nome_exibicao")
    if nome_exibicao is None:
        nome_exibicao = row["nome_exibicao"]
    else:
        nome_exibicao = nome_exibicao.strip()
    if row["papel"] == "admin" and row["ativo"] == 1:
        if novo_papel != "admin" or novo_ativo == 0:
            if _count_admins_ativos(cursor, exceto_id=id_usuario) < 1:
                conn.close()
                return jsonify({"erro": "deve existir pelo menos um administrador ativo"}), 409
    if id_usuario == session["user_id"] and novo_ativo == 0:
        conn.close()
        return jsonify({"erro": "você não pode desativar a si mesmo"}), 409
    senha = dados.get("senha")
    if senha:
        if len(senha) < 4:
            conn.close()
            return jsonify({"erro": "senha muito curta"}), 400
        cursor.execute(
            "UPDATE usuarios SET senha_hash = ?, papel = ?, nome_exibicao = ?, ativo = ? WHERE id = ?",
            (generate_password_hash(senha, method=_HASH_METHOD), novo_papel, nome_exibicao, novo_ativo, id_usuario),
        )
    else:
        cursor.execute(
            "UPDATE usuarios SET papel = ?, nome_exibicao = ?, ativo = ? WHERE id = ?",
            (novo_papel, nome_exibicao, novo_ativo, id_usuario),
        )
    conn.commit()
    cursor.execute(
        "SELECT id, login, papel, nome_exibicao, ativo, criado_em FROM usuarios WHERE id = ?", (id_usuario,)
    )
    row = cursor.fetchone()
    conn.close()
    return jsonify(_usuario_publico(row))


# --- API comandas ---


@app.route("/api/comandas", methods=["GET"])
@staff_required("admin", "caixa", "garcom")
def listar_comandas():
    situacao = (request.args.get("situacao") or "").strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    if situacao == "aberta":
        cursor.execute(
            """
            SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
            FROM comandas WHERE status = 'aberta' ORDER BY id DESC
            """
        )
    elif situacao == "fechada":
        cursor.execute(
            """
            SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
            FROM comandas WHERE status = 'fechada' ORDER BY COALESCE(fechada_em, criado_em) DESC, id DESC
            """
        )
    else:
        cursor.execute(
            """
            SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
            FROM comandas
            ORDER BY CASE WHEN status = 'aberta' THEN 0 ELSE 1 END, id DESC
            """
        )
    comandas = [_montar_comanda(cursor, row["id"], row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(comandas)


@app.route("/api/comandas/<int:id_comanda>", methods=["GET"])
@staff_required("admin", "caixa", "garcom")
def obter_comanda(id_comanda):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
        FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "comanda não encontrada"}), 404
    comanda = _montar_comanda(cursor, row["id"], row)
    conn.close()
    return jsonify(comanda)


@app.route("/api/comandas", methods=["POST"])
@staff_required("admin", "caixa", "garcom")
def abrir_comanda():
    dados = request.get_json() or {}
    mesa = (dados.get("mesa") or "").strip()
    cliente_nome = (dados.get("cliente_nome") or "").strip()
    id_mesa = dados.get("id_mesa")
    conn = get_db()
    cursor = conn.cursor()
    if id_mesa is not None:
        try:
            id_mesa = int(id_mesa)
        except (TypeError, ValueError):
            return jsonify({"erro": "id_mesa inválido"}), 400
        cursor.execute(
            "SELECT id, numero, status, id_comanda_ativa FROM mesas WHERE id = ?",
            (id_mesa,),
        )
        row_mesa = cursor.fetchone()
        if not row_mesa:
            conn.close()
            return jsonify({"erro": "mesa não encontrada"}), 404
        if row_mesa["status"] == "reservada":
            conn.close()
            return jsonify({"erro": "mesa reservada — altere o status no cadastro de mesas"}), 409
        if row_mesa["status"] == "ocupada" and row_mesa["id_comanda_ativa"]:
            conn.close()
            return jsonify({"erro": "mesa já possui comanda aberta"}), 409
        mesa = row_mesa["numero"]
    if not mesa:
        conn.close()
        return jsonify({"erro": "informe a mesa ou referência (balcão, mesa, etc.)"}), 400
    cursor.execute(
        """
        INSERT INTO comandas (mesa, cliente_nome, status, pagamento_status, id_mesa)
        VALUES (?, ?, 'aberta', 'pendente', ?)
        """,
        (mesa, cliente_nome, id_mesa if id_mesa is not None else None),
    )
    id_comanda = cursor.lastrowid
    if id_mesa is not None:
        err = _ocupar_mesa_para_comanda(cursor, id_mesa, id_comanda)
        if err:
            conn.rollback()
            conn.close()
            return jsonify({"erro": err}), 409
    conn.commit()
    cursor.execute(
        """
        SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
        FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    comanda = _montar_comanda(cursor, id_comanda, row)
    conn.close()
    return jsonify(comanda), 201


@app.route("/api/comandas/<int:id_comanda>", methods=["PUT"])
@staff_required("admin", "caixa", "garcom")
def atualizar_itens_comanda(id_comanda):
    dados = request.get_json() or {}
    itens = dados.get("itens", [])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
        FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "comanda não encontrada"}), 404
    if not _pode_editar_itens(row):
        conn.close()
        return jsonify({"erro": "comanda fechou ou já foi paga: não é possível alterar itens"}), 409
    linhas = []
    for item in itens:
        id_item = item.get("id_item")
        quantidade = int(item.get("quantidade", 1))
        if id_item and quantidade > 0:
            linhas.append((id_comanda, id_item, quantidade))
    cursor.execute("DELETE FROM itens_comanda WHERE id_comanda = ?", (id_comanda,))
    for id_c, id_item, quantidade in linhas:
        cursor.execute(
            "INSERT INTO itens_comanda (id_comanda, id_item, quantidade) VALUES (?, ?, ?)",
            (id_c, id_item, quantidade),
        )
    conn.commit()
    cursor.execute(
        """
        SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
        FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    comanda = _montar_comanda(cursor, id_comanda, row)
    conn.close()
    return jsonify(comanda)


@app.route("/api/comandas/<int:id_comanda>/pagamento", methods=["PATCH"])
@staff_required("admin", "caixa")
def pagar_comanda(id_comanda):
    dados = request.get_json() or {}
    pag = dados.get("pagamento_status")
    if pag != "pago":
        return jsonify({"erro": "use pagamento_status: pago para quitar a comanda"}), 400
    forma = dados.get("forma_pagamento")
    if not forma or forma not in FORMAS_PAGAMENTO:
        return jsonify({"erro": "informe forma_pagamento: dinheiro, pix ou cartao"}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
            FROM comandas WHERE id = ?
            """,
            (id_comanda,),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"erro": "comanda não encontrada"}), 404
        if row["status"] == "fechada" or row["pagamento_status"] == "pago":
            conn.rollback()
            return jsonify({"erro": "esta comanda já está fechada"}), 409
        comanda_prev = _montar_comanda(cursor, id_comanda, row)
        if comanda_prev["total"] <= 0 or not comanda_prev["itens"]:
            conn.rollback()
            return jsonify({"erro": "adicione pelo menos um item à comanda antes de registrar o pagamento"}), 400
        consumos = _calcular_consumo_insumos_comanda(cursor, id_comanda)
        if consumos:
            err_est = _validar_e_baixar_estoque(cursor, consumos)
            if err_est:
                conn.rollback()
                return jsonify({"erro": err_est}), 409
        agora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        valor_quitacao = float(comanda_prev["total"])
        cursor.execute(
            """
            UPDATE comandas
            SET pagamento_status = 'pago', forma_pagamento = ?, status = 'fechada', fechada_em = ?, total_quitacao = ?
            WHERE id = ?
            """,
            (forma, agora, valor_quitacao, id_comanda),
        )
        _liberar_mesa_por_comanda(cursor, id_comanda)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status, forma_pagamento, fechada_em, total_quitacao
        FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    comanda = _montar_comanda(cursor, id_comanda, row)
    conn.close()
    return jsonify(comanda)


@app.route("/api/comandas/<int:id_comanda>", methods=["DELETE"])
@staff_required("admin", "caixa", "garcom")
def excluir_comanda(id_comanda):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, status, pagamento_status FROM comandas WHERE id = ?
        """,
        (id_comanda,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "comanda não encontrada"}), 404
    if not _pode_excluir(row):
        conn.close()
        return jsonify({"erro": "só é possível excluir comandas abertas e não pagas"}), 409
    cursor.execute("DELETE FROM itens_comanda WHERE id_comanda = ?", (id_comanda,))
    _liberar_mesa_por_comanda(cursor, id_comanda)
    cursor.execute("DELETE FROM comandas WHERE id = ?", (id_comanda,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "comanda excluída"}), 200


def _montar_mesa_publica(cursor, row):
    resumo = None
    id_comanda = row["id_comanda_ativa"]
    if id_comanda:
        cursor.execute(
            """
            SELECT id, criado_em, mesa, id_mesa, cliente_nome, status, pagamento_status,
                   forma_pagamento, fechada_em, total_quitacao
            FROM comandas WHERE id = ?
            """,
            (id_comanda,),
        )
        c_row = cursor.fetchone()
        if c_row and c_row["status"] == "aberta":
            comanda = _montar_comanda(cursor, id_comanda, c_row)
            resumo = {
                "id": comanda["id"],
                "cliente_nome": comanda["cliente_nome"],
                "total": comanda["total"],
                "itens_count": len(comanda["itens"]),
            }
        else:
            cursor.execute(
                "UPDATE mesas SET status = 'livre', id_comanda_ativa = NULL WHERE id = ?",
                (row["id"],),
            )
            id_comanda = None
    status = row["status"]
    if not id_comanda and status == "ocupada":
        status = "livre"
    return {
        "id": row["id"],
        "numero": row["numero"],
        "capacidade": row["capacidade"],
        "status": status,
        "id_comanda_ativa": id_comanda,
        "comanda": resumo,
    }


# --- API mesas ---


@app.route("/api/mesas", methods=["GET"])
@staff_required("admin", "caixa", "garcom")
def listar_mesas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, numero, capacidade, status, id_comanda_ativa
        FROM mesas
        ORDER BY CAST(numero AS INTEGER), numero
        """
    )
    mesas = [_montar_mesa_publica(cursor, row) for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    return jsonify(mesas)


@app.route("/api/mesas", methods=["POST"])
@staff_required("admin")
def criar_mesa():
    dados = request.get_json() or {}
    numero = (dados.get("numero") or "").strip()
    if not numero:
        return jsonify({"erro": "informe o número da mesa"}), 400
    try:
        capacidade = int(dados.get("capacidade", 4))
    except (TypeError, ValueError):
        return jsonify({"erro": "capacidade inválida"}), 400
    if capacidade < 1:
        return jsonify({"erro": "capacidade deve ser pelo menos 1"}), 400
    status = (dados.get("status") or "livre").strip().lower()
    if status not in MESA_STATUS:
        return jsonify({"erro": "status deve ser livre, ocupada ou reservada"}), 400
    if status == "ocupada":
        return jsonify({"erro": "não é possível cadastrar mesa já como ocupada"}), 400
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO mesas (numero, capacidade, status)
            VALUES (?, ?, ?)
            """,
            (numero, capacidade, status),
        )
        id_mesa = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "já existe mesa com este número"}), 409
    cursor.execute(
        "SELECT id, numero, capacidade, status, id_comanda_ativa FROM mesas WHERE id = ?",
        (id_mesa,),
    )
    row = cursor.fetchone()
    mesa = _montar_mesa_publica(cursor, row)
    conn.close()
    return jsonify(mesa), 201


@app.route("/api/mesas/<int:id_mesa>", methods=["PUT"])
@staff_required("admin")
def atualizar_mesa(id_mesa):
    dados = request.get_json() or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, numero, capacidade, status, id_comanda_ativa FROM mesas WHERE id = ?",
        (id_mesa,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "mesa não encontrada"}), 404
    numero = (dados.get("numero") if "numero" in dados else row["numero"]).strip()
    if not numero:
        conn.close()
        return jsonify({"erro": "número da mesa não pode ficar vazio"}), 400
    capacidade = row["capacidade"]
    if "capacidade" in dados:
        try:
            capacidade = int(dados["capacidade"])
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"erro": "capacidade inválida"}), 400
        if capacidade < 1:
            conn.close()
            return jsonify({"erro": "capacidade deve ser pelo menos 1"}), 400
    status = row["status"]
    if "status" in dados:
        status = (dados.get("status") or "").strip().lower()
        if status not in MESA_STATUS:
            conn.close()
            return jsonify({"erro": "status deve ser livre, ocupada ou reservada"}), 400
        if row["id_comanda_ativa"] and status in ("livre", "reservada"):
            conn.close()
            return jsonify({"erro": "mesa com comanda aberta — feche ou exclua a comanda antes de alterar o status"}), 409
        if status == "ocupada" and not row["id_comanda_ativa"]:
            conn.close()
            return jsonify({"erro": "só marque ocupada ao abrir uma comanda no salão"}), 400
    try:
        cursor.execute(
            """
            UPDATE mesas SET numero = ?, capacidade = ?, status = ?
            WHERE id = ?
            """,
            (numero, capacidade, status, id_mesa),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": "já existe outra mesa com este número"}), 409
    cursor.execute(
        "SELECT id, numero, capacidade, status, id_comanda_ativa FROM mesas WHERE id = ?",
        (id_mesa,),
    )
    mesa = _montar_mesa_publica(cursor, cursor.fetchone())
    conn.close()
    return jsonify(mesa)


@app.route("/api/mesas/<int:id_mesa>", methods=["DELETE"])
@staff_required("admin")
def excluir_mesa(id_mesa):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, status, id_comanda_ativa FROM mesas WHERE id = ?",
        (id_mesa,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "mesa não encontrada"}), 404
    if row["id_comanda_ativa"]:
        conn.close()
        return jsonify({"erro": "não é possível excluir mesa com comanda aberta"}), 409
    if row["status"] == "ocupada":
        conn.close()
        return jsonify({"erro": "mesa consta como ocupada"}), 409
    cursor.execute("DELETE FROM mesas WHERE id = ?", (id_mesa,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "mesa excluída"}), 200


# --- API insumos, notas de compra, composição e financeiro ---


@app.route("/api/insumos", methods=["GET"])
@staff_required("admin")
def listar_insumos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, nome, unidade, estoque_atual, COALESCE(estoque_minimo, 0) AS estoque_minimo, criado_em
        FROM insumos ORDER BY nome
        """
    )
    lista = [
        {
            "id": r["id"],
            "nome": r["nome"],
            "unidade": r["unidade"],
            "estoque_atual": round(float(r["estoque_atual"]), 4),
            "estoque_minimo": round(float(r["estoque_minimo"]), 4),
            "criado_em": r["criado_em"],
            "alerta_estoque": (
                float(r["estoque_atual"]) <= 0
                or (
                    float(r["estoque_minimo"]) > 0 and float(r["estoque_atual"]) <= float(r["estoque_minimo"])
                )
            ),
        }
        for r in cursor.fetchall()
    ]
    conn.close()
    return jsonify(lista)


@app.route("/api/insumos", methods=["POST"])
@staff_required("admin")
def criar_insumo():
    dados = request.get_json() or {}
    nome = (dados.get("nome") or "").strip()
    unidade = (dados.get("unidade") or "un").strip() or "un"
    estoque = dados.get("estoque_atual")
    estoque_min = dados.get("estoque_minimo")
    if not nome:
        return jsonify({"erro": "nome é obrigatório"}), 400
    try:
        estoque = float(estoque) if estoque is not None else 0.0
    except (TypeError, ValueError):
        return jsonify({"erro": "estoque_atual inválido"}), 400
    try:
        estoque_min = float(estoque_min) if estoque_min is not None else 0.0
    except (TypeError, ValueError):
        return jsonify({"erro": "estoque_minimo inválido"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO insumos (nome, unidade, estoque_atual, estoque_minimo) VALUES (?, ?, ?, ?)",
        (nome, unidade, estoque, max(0.0, estoque_min)),
    )
    conn.commit()
    uid = cursor.lastrowid
    cursor.execute(
        """
        SELECT id, nome, unidade, estoque_atual, COALESCE(estoque_minimo, 0) AS estoque_minimo, criado_em
        FROM insumos WHERE id = ?
        """,
        (uid,),
    )
    row = cursor.fetchone()
    conn.close()
    return jsonify(
        {
            "id": row["id"],
            "nome": row["nome"],
            "unidade": row["unidade"],
            "estoque_atual": round(float(row["estoque_atual"]), 4),
            "estoque_minimo": round(float(row["estoque_minimo"]), 4),
            "criado_em": row["criado_em"],
        }
    ), 201


@app.route("/api/insumos/<int:id_insumo>", methods=["PUT"])
@staff_required("admin")
def atualizar_insumo(id_insumo):
    dados = request.get_json() or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM insumos WHERE id = ?", (id_insumo,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "insumo não encontrado"}), 404
    nome = dados.get("nome")
    unidade = dados.get("unidade")
    estoque = dados.get("estoque_atual")
    estoque_min = dados.get("estoque_minimo")
    if nome is not None:
        cursor.execute("UPDATE insumos SET nome = ? WHERE id = ?", (nome.strip(), id_insumo))
    if unidade is not None:
        cursor.execute("UPDATE insumos SET unidade = ? WHERE id = ?", (str(unidade).strip() or "un", id_insumo))
    if estoque is not None:
        try:
            estoque = float(estoque)
            cursor.execute("UPDATE insumos SET estoque_atual = ? WHERE id = ?", (estoque, id_insumo))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"erro": "estoque_atual inválido"}), 400
    if estoque_min is not None:
        try:
            estoque_min = float(estoque_min)
            cursor.execute(
                "UPDATE insumos SET estoque_minimo = ? WHERE id = ?",
                (max(0.0, estoque_min), id_insumo),
            )
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"erro": "estoque_minimo inválido"}), 400
    conn.commit()
    cursor.execute(
        """
        SELECT id, nome, unidade, estoque_atual, COALESCE(estoque_minimo, 0) AS estoque_minimo, criado_em
        FROM insumos WHERE id = ?
        """,
        (id_insumo,),
    )
    row = cursor.fetchone()
    conn.close()
    return jsonify(
        {
            "id": row["id"],
            "nome": row["nome"],
            "unidade": row["unidade"],
            "estoque_atual": round(float(row["estoque_atual"]), 4),
            "estoque_minimo": round(float(row["estoque_minimo"]), 4),
            "criado_em": row["criado_em"],
        }
    )


@app.route("/api/insumos/<int:id_insumo>", methods=["DELETE"])
@staff_required("admin")
def excluir_insumo(id_insumo):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM composicao_item WHERE id_insumo = ?", (id_insumo,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return jsonify({"erro": "insumo usado em receita de cardápio"}), 409
    cursor.execute("SELECT COUNT(*) FROM itens_nota_compra WHERE id_insumo = ?", (id_insumo,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return jsonify({"erro": "insumo já consta em notas de compra"}), 409
    cursor.execute("DELETE FROM insumos WHERE id = ?", (id_insumo,))
    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return jsonify({"erro": "insumo não encontrado"}), 404
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "insumo excluído"})


@app.route("/api/notas-compra", methods=["GET"])
@staff_required("admin")
def listar_notas_compra():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT n.id, n.fornecedor, n.numero_nota, n.data_nota, n.criado_em,
               COALESCE(SUM(ic.quantidade * ic.valor_unitario), 0) AS valor_total
        FROM notas_compra n
        LEFT JOIN itens_nota_compra ic ON ic.id_nota = n.id
        GROUP BY n.id
        ORDER BY n.criado_em DESC
        """
    )
    lista = []
    for r in cursor.fetchall():
        lista.append(
            {
                "id": r["id"],
                "fornecedor": r["fornecedor"],
                "numero_nota": r["numero_nota"],
                "data_nota": r["data_nota"],
                "criado_em": r["criado_em"],
                "valor_total": round(float(r["valor_total"]), 2),
            }
        )
    conn.close()
    return jsonify(lista)


@app.route("/api/notas-compra", methods=["POST"])
@staff_required("admin")
def criar_nota_compra():
    dados = request.get_json() or {}
    fornecedor = (dados.get("fornecedor") or "").strip()
    numero_nota = (dados.get("numero_nota") or "").strip()
    data_nota = (dados.get("data_nota") or "").strip()
    observacao = (dados.get("observacao") or "").strip()
    itens = dados.get("itens") or []
    if not itens:
        return jsonify({"erro": "informe ao menos um item na nota"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO notas_compra (fornecedor, numero_nota, data_nota, observacao)
        VALUES (?, ?, ?, ?)
        """,
        (fornecedor, numero_nota, data_nota, observacao),
    )
    id_nota = cursor.lastrowid
    for linha in itens:
        id_insumo = linha.get("id_insumo")
        try:
            qtd = float(linha.get("quantidade", 0))
            vu = float(linha.get("valor_unitario", 0))
        except (TypeError, ValueError):
            conn.rollback()
            conn.close()
            return jsonify({"erro": "quantidade e valor_unitario devem ser numéricos"}), 400
        if not id_insumo or qtd <= 0:
            conn.rollback()
            conn.close()
            return jsonify({"erro": "cada item precisa de id_insumo e quantidade > 0"}), 400
        cursor.execute("SELECT id FROM insumos WHERE id = ?", (id_insumo,))
        if not cursor.fetchone():
            conn.rollback()
            conn.close()
            return jsonify({"erro": "insumo %s não encontrado" % id_insumo}), 400
        cursor.execute(
            """
            INSERT INTO itens_nota_compra (id_nota, id_insumo, quantidade, valor_unitario)
            VALUES (?, ?, ?, ?)
            """,
            (id_nota, id_insumo, qtd, vu),
        )
        cursor.execute(
            "UPDATE insumos SET estoque_atual = estoque_atual + ? WHERE id = ?",
            (qtd, id_insumo),
        )
    conn.commit()
    conn.close()
    return jsonify({"id": id_nota, "mensagem": "nota registrada e estoque atualizado"}), 201


@app.route("/api/cardapio/<int:id_item>/composicao", methods=["GET"])
@staff_required("admin")
def obter_composicao(id_item):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM itens_cardapio WHERE id = ?", (id_item,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "item do cardápio não encontrado"}), 404
    cursor.execute(
        """
        SELECT c.id_insumo, c.quantidade, i.nome, i.unidade
        FROM composicao_item c
        JOIN insumos i ON i.id = c.id_insumo
        WHERE c.id_item_cardapio = ?
        """,
        (id_item,),
    )
    linhas = [
        {
            "id_insumo": r["id_insumo"],
            "quantidade": float(r["quantidade"]),
            "nome_insumo": r["nome"],
            "unidade": r["unidade"],
        }
        for r in cursor.fetchall()
    ]
    conn.close()
    return jsonify({"id_item": id_item, "itens": linhas})


@app.route("/api/cardapio/<int:id_item>/composicao", methods=["PUT"])
@staff_required("admin")
def salvar_composicao(id_item):
    dados = request.get_json() or {}
    itens = dados.get("itens", [])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM itens_cardapio WHERE id = ?", (id_item,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "item do cardápio não encontrado"}), 404
    cursor.execute("DELETE FROM composicao_item WHERE id_item_cardapio = ?", (id_item,))
    for linha in itens:
        id_insumo = linha.get("id_insumo")
        try:
            qtd = float(linha.get("quantidade", 0))
        except (TypeError, ValueError):
            conn.rollback()
            conn.close()
            return jsonify({"erro": "quantidade inválida"}), 400
        if not id_insumo or qtd <= 0:
            continue
        cursor.execute("SELECT id FROM insumos WHERE id = ?", (id_insumo,))
        if not cursor.fetchone():
            conn.rollback()
            conn.close()
            return jsonify({"erro": "insumo %s não encontrado" % id_insumo}), 400
        cursor.execute(
            """
            INSERT INTO composicao_item (id_item_cardapio, id_insumo, quantidade)
            VALUES (?, ?, ?)
            """,
            (id_item, id_insumo, qtd),
        )
    conn.commit()
    conn.close()
    return obter_composicao(id_item)


@app.route("/api/financeiro/resumo", methods=["GET"])
@staff_required("admin", "caixa")
def financeiro_resumo():
    ini_s = (request.args.get("inicio") or "").strip()
    fim_s = (request.args.get("fim") or "").strip()
    try:
        fim = datetime.strptime(fim_s, "%Y-%m-%d").date() if fim_s else date.today()
        inicio = datetime.strptime(ini_s, "%Y-%m-%d").date() if ini_s else (fim - timedelta(days=30))
    except ValueError:
        return jsonify({"erro": "use datas no formato YYYY-MM-DD"}), 400
    if inicio > fim:
        return jsonify({"erro": "data início maior que fim"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(total_quitacao), 0) AS receita, COUNT(*) AS qtd
        FROM comandas
        WHERE status = 'fechada' AND pagamento_status = 'pago'
          AND date(fechada_em) BETWEEN date(?) AND date(?)
        """,
        (inicio.isoformat(), fim.isoformat()),
    )
    r1 = cursor.fetchone()
    cursor.execute(
        """
        SELECT forma_pagamento, COALESCE(SUM(total_quitacao), 0) AS sub, COUNT(*) AS qtd
        FROM comandas
        WHERE status = 'fechada' AND pagamento_status = 'pago'
          AND date(fechada_em) BETWEEN date(?) AND date(?)
        GROUP BY forma_pagamento
        """,
        (inicio.isoformat(), fim.isoformat()),
    )
    por_forma = []
    for r in cursor.fetchall():
        por_forma.append(
            {
                "forma_pagamento": r["forma_pagamento"],
                "total": round(float(r["sub"]), 2),
                "comandas": r["qtd"],
            }
        )
    cursor.execute(
        """
        SELECT COALESCE(SUM(ic.quantidade * ic.valor_unitario), 0) AS gasto
        FROM itens_nota_compra ic
        JOIN notas_compra n ON n.id = ic.id_nota
        WHERE date(n.criado_em) BETWEEN date(?) AND date(?)
        """,
        (inicio.isoformat(), fim.isoformat()),
    )
    gasto = round(float(cursor.fetchone()["gasto"]), 2)
    conn.close()
    return jsonify(
        {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "receita_vendas": round(float(r1["receita"]), 2),
            "comandas_fechadas": r1["qtd"],
            "por_forma_pagamento": por_forma,
            "compras_registradas_valor": gasto,
        }
    )


@app.route("/api/admin/dashboard", methods=["GET"])
@staff_required("admin")
def admin_dashboard():
    hoje = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM comandas WHERE status = 'aberta'")
    comandas_abertas = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT COALESCE(SUM(total_quitacao), 0)
        FROM comandas
        WHERE status = 'fechada' AND pagamento_status = 'pago'
          AND date(fechada_em) = date(?)
        """,
        (hoje,),
    )
    receita_hoje = round(float(cursor.fetchone()[0]), 2)
    cursor.execute("SELECT COUNT(*) FROM insumos WHERE estoque_atual <= 0")
    insumos_sem_estoque = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT COUNT(*) FROM insumos
        WHERE estoque_atual > 0 AND estoque_minimo > 0 AND estoque_atual <= estoque_minimo
        """
    )
    insumos_abaixo_minimo = cursor.fetchone()[0]
    conn.close()
    return jsonify(
        {
            "comandas_abertas": comandas_abertas,
            "receita_hoje": receita_hoje,
            "insumos_sem_estoque": insumos_sem_estoque,
            "insumos_abaixo_minimo": insumos_abaixo_minimo,
        }
    )


@app.route("/api/financeiro/ranking-itens", methods=["GET"])
@staff_required("admin", "caixa")
def financeiro_ranking_itens():
    ini_s = (request.args.get("inicio") or "").strip()
    fim_s = (request.args.get("fim") or "").strip()
    try:
        lim_raw = request.args.get("limit") or "15"
        lim = min(max(int(lim_raw), 1), 100)
    except ValueError:
        return jsonify({"erro": "limit deve ser inteiro"}), 400
    try:
        fim = datetime.strptime(fim_s, "%Y-%m-%d").date() if fim_s else date.today()
        inicio = datetime.strptime(ini_s, "%Y-%m-%d").date() if ini_s else (fim - timedelta(days=30))
    except ValueError:
        return jsonify({"erro": "use datas no formato YYYY-MM-DD"}), 400
    if inicio > fim:
        return jsonify({"erro": "data início maior que fim"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ic.id_item, c.nome,
               SUM(ic.quantidade) AS qtd,
               SUM(ic.quantidade * c.preco) AS receita
        FROM itens_comanda ic
        JOIN comandas co ON co.id = ic.id_comanda
        JOIN itens_cardapio c ON c.id = ic.id_item
        WHERE co.status = 'fechada' AND co.pagamento_status = 'pago'
          AND date(co.fechada_em) BETWEEN date(?) AND date(?)
        GROUP BY ic.id_item
        ORDER BY qtd DESC
        LIMIT ?
        """,
        (inicio.isoformat(), fim.isoformat(), lim),
    )
    ranking = [
        {
            "id_item": r["id_item"],
            "nome": r["nome"],
            "quantidade_vendida": int(round(float(r["qtd"]))),
            "receita": round(float(r["receita"]), 2),
        }
        for r in cursor.fetchall()
    ]
    conn.close()
    return jsonify(
        {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "limit": lim,
            "itens": ranking,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
