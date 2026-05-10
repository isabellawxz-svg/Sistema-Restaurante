/**
 * app.js
 * Cardápio, comandas (conta aberta até pagamento) e admin do cardápio.
 */

let itensCardapio = [];

var LABEL_FORMA_PAGAMENTO = { dinheiro: "Dinheiro", pix: "PIX", cartao: "Cartão" };

function perfilComandasAtual() {
    return window.PERFIL_COMANDAS || "garcom";
}

async function apiFetch(url, options) {
    const res = await fetch(url, options || {});
    if (res.status === 401) {
        window.location.href = "/login";
        return null;
    }
    return res;
}

async function carregarCardapio() {
    try {
        const res = await apiFetch("/api/cardapio");
        if (!res) return;
        itensCardapio = await res.json();
        const ul = document.getElementById("lista-cardapio");
        if (ul) {
            ul.innerHTML = "";
            itensCardapio.forEach(function(item) {
                const li = document.createElement("li");
                var suf = item.categoria ? " · " + item.categoria : "";
                li.textContent = item.nome + suf + " — R$ " + item.preco.toFixed(2);
                ul.appendChild(li);
            });
        }
    } catch (err) {
        console.error("Erro ao carregar cardápio:", err);
    }
}

async function abrirComanda() {
    const mesa = document.getElementById("comanda-mesa").value.trim();
    const clienteNome = document.getElementById("comanda-cliente").value.trim();
    const msg = document.getElementById("msg-comanda");
    if (!mesa) {
        msg.textContent = "Informe a mesa ou referência.";
        return;
    }
    try {
        const res = await apiFetch("/api/comandas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mesa: mesa, cliente_nome: clienteNome })
        });
        if (!res) return;
        const data = await res.json();
        if (res.ok) {
            msg.textContent = "Comanda #" + data.id + " aberta. Use «Editar itens» nela para lançar o consumo.";
            document.getElementById("comanda-mesa").value = "";
            document.getElementById("comanda-cliente").value = "";
            carregarComandas();
        } else {
            msg.textContent = data.erro || "Erro ao abrir comanda.";
        }
    } catch (err) {
        msg.textContent = "Erro de conexão.";
        console.error(err);
    }
}

function renderBlocoComanda(ped, divPai, perfil) {
    perfil = perfil || perfilComandasAtual();
    const bloco = document.createElement("div");
    bloco.className = "comanda-bloco";
    bloco.dataset.id = ped.id;
    bloco.dataset.comanda = JSON.stringify(ped);
    const fechada = ped.status === "fechada";
    const badgeStatus = fechada
        ? "<span class=\"badge badge-comanda-fechada\">Fechada</span>"
        : "<span class=\"badge badge-comanda-aberta\">Aberta</span>";
    const pagBadge = ped.pagamento_status === "pago"
        ? "<span class=\"badge badge-pago\">Pago" +
          (ped.forma_pagamento ? " · " + escapeHtml(LABEL_FORMA_PAGAMENTO[ped.forma_pagamento] || ped.forma_pagamento) : "") +
          "</span>"
        : "<span class=\"badge badge-pendente\">Pagamento pendente</span>";
    const refCliente = ped.cliente_nome
        ? "<span class=\"meta-linha\">Cliente: " + escapeHtml(ped.cliente_nome) + "</span>"
        : "";
    let html = "<div class=\"comanda-cabecalho\"><div><strong>Comanda #" + ped.id + "</strong> " +
        badgeStatus + " " + pagBadge +
        "</div><div class=\"comanda-meta\">" +
        "<span class=\"meta-linha\">Mesa: " + escapeHtml(ped.mesa || "—") + "</span>" +
        refCliente +
        "<span class=\"meta-linha\">Aberta em: " + escapeHtml(ped.criado_em) + "</span>";
    if (fechada && ped.fechada_em) {
        html += "<span class=\"meta-linha\">Fechada em: " + escapeHtml(ped.fechada_em) + "</span>";
    }
    html += "<span class=\"meta-linha total-comanda\">Total: R$ " + Number(ped.total).toFixed(2) + "</span>" +
        "</div></div>";
    if (ped.itens.length === 0) {
        const msgVazia = perfil === "caixa"
            ? "Sem itens lançados — aguardando o salão."
            : "Nenhum item lançado — use «Editar itens» para incluir do cardápio.";
        html += "<p class=\"comanda-vazia-msg\">" + msgVazia + "</p>";
    } else {
        html += "<ul class=\"lista-itens-comanda\">";
        ped.itens.forEach(function(item) {
            html += "<li>" + item.quantidade + "× " + escapeHtml(item.nome) + " — R$ " +
                (item.quantidade * item.preco).toFixed(2) + "</li>";
        });
        html += "</ul>";
    }
    if (!fechada && perfil === "caixa") {
        html += "<div class=\"fluxo-pagamento\"><span class=\"fluxo-titulo\">Pagamento</span>";
        if (ped.pagamento_status === "pendente") {
            html += "<div class=\"linha-pagamento\">" +
                "<label>Forma <select class=\"select-forma-pagamento\" data-id=\"" + ped.id + "\">" +
                "<option value=\"\">Escolha…</option>" +
                "<option value=\"dinheiro\">Dinheiro</option>" +
                "<option value=\"pix\">PIX</option>" +
                "<option value=\"cartao\">Cartão</option></select></label> " +
                "<button type=\"button\" class=\"btn-registrar-pago\" data-id=\"" + ped.id + "\">Pagar e fechar comanda</button></div>" +
                "<p class=\"fluxo-msg dica-pagamento\">Ao pagar, a comanda fecha e baixa estoque conforme a ficha técnica.</p>";
        }
        html += "</div>";
    }
    html += "<div class=\"acoes-comanda\">";
    if ((perfil === "garcom" || perfil === "caixa") && ped.pode_editar_itens) {
        html += "<button type=\"button\" class=\"btn-lancar-modal\" data-id=\"" + ped.id + "\">Lançar / editar itens</button>";
    }
    if ((perfil === "garcom" || perfil === "caixa") && ped.pode_excluir) {
        html += "<button type=\"button\" class=\"btn-excluir-comanda\">Excluir comanda</button>";
    }
    html += "</div>";
    bloco.innerHTML = html;
    divPai.appendChild(bloco);

    bloco.querySelectorAll(".btn-excluir-comanda").forEach(function(btn) {
        btn.addEventListener("click", function() {
            const id = bloco.dataset.id;
            if (confirm("Excluir a comanda #" + id + "?")) excluirComanda(id);
        });
    });
    bloco.querySelectorAll(".btn-lancar-modal").forEach(function(btn) {
        btn.addEventListener("click", function() {
            if (typeof abrirModalLancamentoComanda === "function") {
                abrirModalLancamentoComanda(parseInt(btn.dataset.id, 10));
            }
        });
    });
    bloco.querySelectorAll(".btn-registrar-pago").forEach(function(btn) {
        btn.addEventListener("click", function() {
            const id = parseInt(btn.dataset.id, 10);
            const sel = bloco.querySelector(".select-forma-pagamento");
            const forma = sel ? sel.value : "";
            patchPagamentoComanda(id, forma);
        });
    });
}

async function carregarComandas() {
    const perfil = perfilComandasAtual();
    try {
        const resAb = await apiFetch("/api/comandas?situacao=aberta");
        const resFe = await apiFetch("/api/comandas?situacao=fechada");
        if (!resAb || !resFe) return;
        const abertas = await resAb.json();
        const fechadas = await resFe.json();
        const divAb = document.getElementById("lista-comandas-abertas");
        const divFe = document.getElementById("lista-comandas-fechadas");
        if (!divAb || !divFe) return;
        divAb.innerHTML = "";
        divFe.innerHTML = "";
        if (abertas.length === 0) {
            divAb.innerHTML = "<p class=\"lista-vazia\">Nenhuma comanda aberta.</p>";
        } else {
            abertas.forEach(function(c) { renderBlocoComanda(c, divAb, perfil); });
        }
        if (fechadas.length === 0) {
            divFe.innerHTML = "<p class=\"lista-vazia\">Nenhuma comanda fechada ainda.</p>";
        } else {
            fechadas.forEach(function(c) { renderBlocoComanda(c, divFe, perfil); });
        }
    } catch (err) {
        console.error("Erro ao carregar comandas:", err);
    }
}

async function patchPagamentoComanda(idComanda, formaPagamento) {
    try {
        const res = await apiFetch("/api/comandas/" + idComanda + "/pagamento", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pagamento_status: "pago", forma_pagamento: formaPagamento })
        });
        if (!res) return;
        const data = await res.json();
        if (!res.ok) {
            alert(data.erro || "Não foi possível registrar o pagamento.");
            return;
        }
        carregarComandas();
    } catch (e) {
        alert("Erro de conexão.");
        console.error(e);
    }
}

async function excluirComanda(id) {
    try {
        const res = await apiFetch("/api/comandas/" + id, { method: "DELETE" });
        if (!res) return;
        if (res.ok) {
            carregarComandas();
        } else {
            const data = await res.json();
            alert(data.erro || "Erro ao excluir comanda.");
        }
    } catch (err) {
        alert("Erro de conexão.");
        console.error(err);
    }
}

function escapeHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
}

async function carregarCardapioAdmin() {
    try {
        const res = await apiFetch("/api/cardapio");
        if (!res) return;
        const itens = await res.json();
        const ul = document.getElementById("lista-itens-admin");
        ul.innerHTML = "";
        itens.forEach(function(item) {
            const li = document.createElement("li");
            li.className = "item-cardapio";
            li.dataset.id = item.id;
            li.dataset.nome = item.nome;
            li.dataset.preco = String(item.preco);
            li.dataset.categoria = item.categoria || "";
            var badge = item.categoria
                ? "<span class=\"item-cat-badge\">" + escapeHtml(item.categoria) + "</span> "
                : "";
            li.innerHTML = "<span class=\"texto-item\">" + badge + escapeHtml(item.nome) + " — R$ " + item.preco.toFixed(2) + "</span><span class=\"botoes-item\"><button type=\"button\" class=\"btn-editar-item\">Editar</button><button type=\"button\" class=\"btn-excluir-item\">Excluir</button></span>";
            ul.appendChild(li);
        });
        ul.querySelectorAll(".btn-excluir-item").forEach(function(btn) {
            btn.addEventListener("click", function() {
                const id = btn.closest(".item-cardapio").dataset.id;
                if (confirm("Excluir este item do cardápio?")) excluirItem(id);
            });
        });
        ul.querySelectorAll(".btn-editar-item").forEach(function(btn) {
            btn.addEventListener("click", function() {
                const li = btn.closest(".item-cardapio");
                const id = parseInt(li.dataset.id, 10);
                const nome = li.dataset.nome || "";
                const preco = li.dataset.preco || "0";
                const categoria = li.dataset.categoria || "";
                mostrarFormEditarItem(li, id, nome, preco, categoria);
            });
        });
    } catch (err) {
        console.error("Erro ao carregar cardápio (admin):", err);
    }
}

async function excluirItem(id) {
    try {
        const res = await apiFetch("/api/cardapio/" + id, { method: "DELETE" });
        if (!res) return;
        if (res.ok) {
            carregarCardapioAdmin();
        } else {
            const data = await res.json();
            alert(data.erro || "Erro ao excluir item.");
        }
    } catch (err) {
        alert("Erro de conexão.");
        console.error(err);
    }
}

function mostrarFormEditarItem(li, id, nomeAtual, precoAtual, categoriaAtual) {
    if (li.querySelector(".form-editar-item")) {
        return;
    }
    const textoEl = li.querySelector(".texto-item");
    const botoesEl = li.querySelector(".botoes-item");
    textoEl.style.display = "none";
    botoesEl.style.display = "none";
    const form = document.createElement("div");
    form.className = "form-editar-item";
    form.innerHTML = "<input type=\"text\" name=\"nome\" value=\"" + escapeHtml(nomeAtual) + "\" placeholder=\"Nome\">" +
        "<input type=\"text\" name=\"categoria\" value=\"" + escapeHtml(categoriaAtual || "") + "\" placeholder=\"Categoria\" maxlength=\"60\">" +
        "<input type=\"number\" name=\"preco\" step=\"0.01\" min=\"0\" value=\"" + escapeHtml(String(precoAtual)) + "\" placeholder=\"Preço\">" +
        "<button type=\"button\" class=\"btn-salvar-item\">Salvar</button><button type=\"button\" class=\"btn-cancelar-item\">Cancelar</button>";
    li.insertBefore(form, botoesEl);
    form.querySelector(".btn-salvar-item").addEventListener("click", async function() {
        const nome = form.querySelector("input[name=nome]").value.trim();
        const preco = parseFloat(form.querySelector("input[name=preco]").value);
        const categoria = form.querySelector("input[name=categoria]").value.trim();
        if (!nome || isNaN(preco)) {
            alert("Preencha nome e preço.");
            return;
        }
        try {
            const res = await apiFetch("/api/cardapio/" + id, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome: nome, preco: preco, categoria: categoria })
            });
            if (!res) return;
            if (res.ok) {
                li.removeChild(form);
                textoEl.style.display = "";
                botoesEl.style.display = "";
                li.dataset.nome = nome;
                li.dataset.preco = String(preco);
                li.dataset.categoria = categoria;
                var badge = categoria
                    ? "<span class=\"item-cat-badge\">" + escapeHtml(categoria) + "</span> "
                    : "";
                textoEl.innerHTML = badge + escapeHtml(nome) + " — R$ " + preco.toFixed(2);
            } else {
                const data = await res.json();
                alert(data.erro || "Erro ao salvar.");
            }
        } catch (err) {
            alert("Erro de conexão.");
        }
    });
    form.querySelector(".btn-cancelar-item").addEventListener("click", function() {
        li.removeChild(form);
        textoEl.style.display = "";
        botoesEl.style.display = "";
    });
}

async function cadastrarItem(ev) {
    ev.preventDefault();
    const nome = document.getElementById("nome").value.trim();
    const preco = parseFloat(document.getElementById("preco").value);
    const msg = document.getElementById("msg-admin");
    if (!nome) {
        msg.textContent = "Informe o nome do item.";
        return;
    }
    try {
        const res = await apiFetch("/api/cardapio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: nome,
                preco: preco,
                categoria: (document.getElementById("categoria") && document.getElementById("categoria").value.trim()) || ""
            })
        });
        if (!res) return;
        const data = await res.json();
        if (res.ok) {
            msg.textContent = "Item cadastrado: " + data.nome;
            document.getElementById("form-item").reset();
            carregarCardapioAdmin();
        } else {
            msg.textContent = data.erro || "Erro ao cadastrar.";
        }
    } catch (err) {
        msg.textContent = "Erro de conexão.";
        console.error(err);
    }
}

var LABEL_PAPEL = { admin: "Administrador", caixa: "Caixa", garcom: "Garçom" };

async function carregarUsuariosAdmin() {
    const div = document.getElementById("lista-usuarios");
    if (!div) return;
    try {
        const res = await apiFetch("/api/usuarios");
        if (!res) return;
        if (!res.ok) {
            div.textContent = "Não foi possível carregar usuários.";
            return;
        }
        const usuarios = await res.json();
        div.innerHTML = "";
        if (usuarios.length === 0) {
            div.innerHTML = "<p class=\"lista-vazia\">Nenhum usuário.</p>";
            return;
        }
        usuarios.forEach(function(u) {
            const bloco = document.createElement("div");
            bloco.className = "usuario-linha";
            const selPapel = "<select class=\"usuario-papel\" data-id=\"" + u.id + "\">" +
                ["garcom", "caixa", "admin"].map(function(p) {
                    return "<option value=\"" + p + "\"" + (u.papel === p ? " selected" : "") + ">" +
                        escapeHtml(LABEL_PAPEL[p]) + "</option>";
                }).join("") + "</select>";
            const chkAtivo = "<label class=\"usuario-ativo\"><input type=\"checkbox\" class=\"usuario-ativo-cb\" data-id=\"" +
                u.id + "\"" + (u.ativo ? " checked" : "") + "> Ativo</label>";
            const inpNome = "<input type=\"text\" class=\"usuario-nome\" data-id=\"" + u.id + "\" value=\"" +
                escapeHtml(u.nome_exibicao) + "\" placeholder=\"Nome\">";
            const inpSenha = "<input type=\"password\" class=\"usuario-senha\" data-id=\"" + u.id +
                "\" placeholder=\"Nova senha (opcional)\">";
            bloco.innerHTML = "<div class=\"usuario-campos\"><strong>" + escapeHtml(u.login) + "</strong> " +
                inpNome + selPapel + chkAtivo + inpSenha +
                "<button type=\"button\" class=\"btn-salvar-usuario\" data-id=\"" + u.id + "\">Salvar</button></div>";
            div.appendChild(bloco);
        });
        div.querySelectorAll(".btn-salvar-usuario").forEach(function(btn) {
            btn.addEventListener("click", function() { salvarUsuarioAdmin(parseInt(btn.dataset.id, 10)); });
        });
    } catch (e) {
        console.error(e);
    }
}

async function salvarUsuarioAdmin(id) {
    const msg = document.getElementById("msg-usuarios");
    const papel = document.querySelector(".usuario-papel[data-id=\"" + id + "\"]").value;
    const nome = document.querySelector(".usuario-nome[data-id=\"" + id + "\"]").value.trim();
    const ativo = document.querySelector(".usuario-ativo-cb[data-id=\"" + id + "\"]").checked;
    const senhaEl = document.querySelector(".usuario-senha[data-id=\"" + id + "\"]");
    const senha = senhaEl.value;
    const body = { papel: papel, nome_exibicao: nome, ativo: ativo };
    if (senha) body.senha = senha;
    try {
        const res = await apiFetch("/api/usuarios/" + id, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        if (!res) return;
        const data = await res.json();
        if (res.ok) {
            msg.textContent = "Usuário atualizado.";
            senhaEl.value = "";
            carregarUsuariosAdmin();
        } else {
            msg.textContent = data.erro || "Erro ao salvar.";
        }
    } catch (e) {
        msg.textContent = "Erro de conexão.";
    }
}

async function cadastrarUsuarioAdmin(ev) {
    ev.preventDefault();
    const msg = document.getElementById("msg-usuarios");
    msg.textContent = "";
    const login = document.getElementById("novo-login").value.trim().toLowerCase();
    const nome = document.getElementById("novo-nome").value.trim();
    const papel = document.getElementById("novo-papel").value;
    const senha = document.getElementById("novo-senha").value;
    try {
        const res = await apiFetch("/api/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ login: login, nome_exibicao: nome, papel: papel, senha: senha })
        });
        if (!res) return;
        const data = await res.json();
        if (res.ok) {
            msg.textContent = "Usuário criado: " + data.login;
            document.getElementById("form-usuario").reset();
            carregarUsuariosAdmin();
        } else {
            msg.textContent = data.erro || "Erro ao criar.";
        }
    } catch (e) {
        msg.textContent = "Erro de conexão.";
    }
}
