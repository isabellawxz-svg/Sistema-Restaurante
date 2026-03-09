# app.py
# Backend da aplicação: servidor Flask que expõe a API REST e serve as páginas HTML.
# Responsável por: conectar ao SQLite, rotas da API (cardápio, pedidos, cadastro de itens)
# e entrega das telas (index = cardápio/pedidos, admin = cadastro de itens).

import sqlite3
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DB_PATH = "dados.db"


def get_db():
    """Abre uma conexão com o banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # retorna linhas como dicionário
    return conn


# --- Rotas que servem páginas HTML ---

@app.route("/")
def index():
    """Página principal: cardápio e área de anotar pedido."""
    return render_template("index.html")


@app.route("/admin")
def admin():
    """Página de administração: cadastro de itens no cardápio."""
    return render_template("admin.html")


# --- Rotas da API (retornam JSON) ---

@app.route("/api/cardapio", methods=["GET"])
def listar_cardapio():
    """GET: retorna lista de todos os itens do cardápio."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, preco FROM itens_cardapio ORDER BY nome")
    itens = [{"id": row["id"], "nome": row["nome"], "preco": row["preco"]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(itens)


@app.route("/api/cardapio", methods=["POST"])
def cadastrar_item():
    """POST: cadastra um novo item no cardápio (nome e preco no body JSON)."""
    dados = request.get_json()
    nome = dados.get("nome")
    preco = dados.get("preco")
    if not nome or preco is None:
        return jsonify({"erro": "nome e preco são obrigatórios"}), 400
    try:
        preco = float(preco)
    except (TypeError, ValueError):
        return jsonify({"erro": "preco deve ser um número"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO itens_cardapio (nome, preco) VALUES (?, ?)", (nome.strip(), preco))
    conn.commit()
    id_novo = cursor.lastrowid
    conn.close()
    return jsonify({"id": id_novo, "nome": nome, "preco": preco}), 201


@app.route("/api/cardapio/<int:id_item>", methods=["PUT"])
def editar_item(id_item):
    """PUT: edita um item do cardápio (nome e/ou preco no body JSON)."""
    dados = request.get_json() or {}
    nome = dados.get("nome")
    preco = dados.get("preco")
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
    conn.commit()
    cursor.execute("SELECT id, nome, preco FROM itens_cardapio WHERE id = ?", (id_item,))
    row = cursor.fetchone()
    conn.close()
    return jsonify({"id": row["id"], "nome": row["nome"], "preco": row["preco"]})


@app.route("/api/cardapio/<int:id_item>", methods=["DELETE"])
def excluir_item(id_item):
    """DELETE: exclui um item do cardápio (e referências em itens_pedido)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM itens_pedido WHERE id_item = ?", (id_item,))
    cursor.execute("DELETE FROM itens_cardapio WHERE id = ?", (id_item,))
    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return jsonify({"erro": "item não encontrado"}), 404
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "item excluído"}), 200


def _montar_pedido(cursor, id_pedido, row):
    """Monta um dicionário do pedido com itens (id_item para edição)."""
    cursor.execute("""
        SELECT ip.id_item, ip.quantidade, c.nome, c.preco
        FROM itens_pedido ip
        JOIN itens_cardapio c ON c.id = ip.id_item
        WHERE ip.id_pedido = ?
    """, (id_pedido,))
    itens = []
    for r in cursor.fetchall():
        itens.append({
            "id_item": r["id_item"],
            "quantidade": r["quantidade"],
            "nome": r["nome"],
            "preco": r["preco"]
        })
    return {"id": id_pedido, "criado_em": row["criado_em"], "itens": itens}


@app.route("/api/pedidos", methods=["GET"])
def listar_pedidos():
    """GET: retorna todos os pedidos com seus itens (para exibir na tela)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, criado_em FROM pedidos ORDER BY id DESC")
    pedidos = [_montar_pedido(cursor, row["id"], row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(pedidos)


@app.route("/api/pedidos/<int:id_pedido>", methods=["GET"])
def obter_pedido(id_pedido):
    """GET: retorna um único pedido com itens (para edição)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, criado_em FROM pedidos WHERE id = ?", (id_pedido,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "pedido não encontrado"}), 404
    pedido = _montar_pedido(cursor, row["id"], row)
    conn.close()
    return jsonify(pedido)


@app.route("/api/pedidos", methods=["POST"])
def criar_pedido():
    """POST: cria um novo pedido. Body: lista de { id_item, quantidade }."""
    dados = request.get_json()
    itens = dados.get("itens", [])
    if not itens:
        return jsonify({"erro": "envie pelo menos um item no pedido"}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pedidos DEFAULT VALUES")
    id_pedido = cursor.lastrowid
    for item in itens:
        id_item = item.get("id_item")
        quantidade = int(item.get("quantidade", 1))
        if id_item and quantidade > 0:
            cursor.execute(
                "INSERT INTO itens_pedido (id_pedido, id_item, quantidade) VALUES (?, ?, ?)",
                (id_pedido, id_item, quantidade)
            )
    conn.commit()
    conn.close()
    return jsonify({"id": id_pedido, "mensagem": "Pedido criado"}), 201


@app.route("/api/pedidos/<int:id_pedido>", methods=["PUT"])
def editar_pedido(id_pedido):
    """PUT: edita um pedido. Body: { itens: [ { id_item, quantidade } ] } (substitui os itens)."""
    dados = request.get_json()
    itens = dados.get("itens", []) if dados else []
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos WHERE id = ?", (id_pedido,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "pedido não encontrado"}), 404
    cursor.execute("DELETE FROM itens_pedido WHERE id_pedido = ?", (id_pedido,))
    for item in itens:
        id_item = item.get("id_item")
        quantidade = int(item.get("quantidade", 1))
        if id_item and quantidade > 0:
            cursor.execute(
                "INSERT INTO itens_pedido (id_pedido, id_item, quantidade) VALUES (?, ?, ?)",
                (id_pedido, id_item, quantidade)
            )
    conn.commit()
    conn.close()
    return jsonify({"id": id_pedido, "mensagem": "Pedido atualizado"})


@app.route("/api/pedidos/<int:id_pedido>", methods=["DELETE"])
def excluir_pedido(id_pedido):
    """DELETE: exclui um pedido e seus itens."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos WHERE id = ?", (id_pedido,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"erro": "pedido não encontrado"}), 404
    cursor.execute("DELETE FROM itens_pedido WHERE id_pedido = ?", (id_pedido,))
    cursor.execute("DELETE FROM pedidos WHERE id = ?", (id_pedido,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "pedido excluído"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
