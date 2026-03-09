/**
 * app.js
 * Comunicação do frontend com a API: busca cardápio, envia pedidos, cadastra itens (admin).
 * Usado tanto na página do cardápio (index) quanto na página admin.
 */

let itensCardapio = [];

/**
 * Busca os itens do cardápio na API (GET /api/cardapio) e preenche a lista na página principal.
 * Também monta os campos de quantidade para "Anotar pedido".
 */
async function carregarCardapio() {
    try {
        const res = await fetch("/api/cardapio");
        itensCardapio = await res.json();
        const ul = document.getElementById("lista-cardapio");
        ul.innerHTML = "";
        itensCardapio.forEach(function(item) {
            const li = document.createElement("li");
            li.textContent = item.nome + " - R$ " + item.preco.toFixed(2);
            ul.appendChild(li);
        });
        montarFormularioPedido();
    } catch (err) {
        console.error("Erro ao carregar cardápio:", err);
    }
}

/**
 * Monta na tela os campos de quantidade para cada item do cardápio (para anotar pedido).
 */
function montarFormularioPedido() {
    const div = document.getElementById("form-pedido");
    div.innerHTML = "";
    itensCardapio.forEach(function(item) {
        const label = document.createElement("label");
        label.textContent = item.nome + " (qtd): ";
        const input = document.createElement("input");
        input.type = "number";
        input.min = 0;
        input.value = 0;
        input.dataset.idItem = item.id;
        input.dataset.nome = item.nome;
        div.appendChild(label);
        div.appendChild(input);
        div.appendChild(document.createElement("br"));
    });
}

/**
 * Envia o pedido para a API (POST /api/pedidos) com os itens que têm quantidade > 0.
 */
async function enviarPedido() {
    const inputs = document.querySelectorAll("#form-pedido input[type=number]");
    const itens = [];
    inputs.forEach(function(input) {
        const qtd = parseInt(input.value, 10);
        if (qtd > 0) {
            itens.push({ id_item: parseInt(input.dataset.idItem, 10), quantidade: qtd });
        }
    });
    if (itens.length === 0) {
        document.getElementById("msg-pedido").textContent = "Selecione pelo menos um item.";
        return;
    }
    try {
        const res = await fetch("/api/pedidos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ itens: itens })
        });
        const data = await res.json();
        if (res.ok) {
            document.getElementById("msg-pedido").textContent = "Pedido #" + data.id + " enviado!";
            inputs.forEach(function(i) { i.value = 0; });
            carregarPedidos();
        } else {
            document.getElementById("msg-pedido").textContent = data.erro || "Erro ao enviar pedido.";
        }
    } catch (err) {
        document.getElementById("msg-pedido").textContent = "Erro de conexão.";
        console.error(err);
    }
}

/**
 * Busca todos os pedidos na API (GET /api/pedidos) e exibe na seção "Pedidos realizados".
 * Inclui botões Editar e Excluir e formulário de edição (quantidades) por pedido.
 */
async function carregarPedidos() {
    try {
        const res = await fetch("/api/pedidos");
        const pedidos = await res.json();
        const div = document.getElementById("lista-pedidos");
        div.innerHTML = "";
        pedidos.forEach(function(ped) {
            const bloco = document.createElement("div");
            bloco.className = "pedido-bloco";
            bloco.dataset.id = ped.id;
            bloco.dataset.pedido = JSON.stringify(ped);
            let html = "<strong>Pedido #" + ped.id + "</strong> (" + ped.criado_em + ")<ul>";
            ped.itens.forEach(function(item) {
                html += "<li>" + item.quantidade + "x " + item.nome + " - R$ " + (item.quantidade * item.preco).toFixed(2) + "</li>";
            });
            html += "</ul><div class=\"acoes-pedido\"><button type=\"button\" class=\"btn-editar-pedido\">Editar</button><button type=\"button\" class=\"btn-excluir-pedido\">Excluir</button></div><div class=\"form-editar-pedido\" style=\"display:none\"></div>";
            bloco.innerHTML = html;
            div.appendChild(bloco);
        });
        // Delegação de eventos: Excluir e Editar
        div.querySelectorAll(".btn-excluir-pedido").forEach(function(btn) {
            btn.addEventListener("click", function() {
                const bloco = btn.closest(".pedido-bloco");
                const id = bloco.dataset.id;
                if (confirm("Excluir o pedido #" + id + "?")) excluirPedido(id);
            });
        });
        div.querySelectorAll(".btn-editar-pedido").forEach(function(btn) {
            btn.addEventListener("click", function() {
                const bloco = btn.closest(".pedido-bloco");
                const id = bloco.dataset.id;
                const pedido = JSON.parse(bloco.dataset.pedido);
                mostrarFormEditarPedido(bloco, parseInt(id, 10), pedido);
            });
        });
    } catch (err) {
        console.error("Erro ao carregar pedidos:", err);
    }
}

/**
 * Exclui um pedido (DELETE /api/pedidos/:id) e recarrega a lista.
 */
async function excluirPedido(id) {
    try {
        const res = await fetch("/api/pedidos/" + id, { method: "DELETE" });
        if (res.ok) {
            carregarPedidos();
        } else {
            const data = await res.json();
            alert(data.erro || "Erro ao excluir pedido.");
        }
    } catch (err) {
        alert("Erro de conexão.");
        console.error(err);
    }
}

/**
 * Mostra o formulário de edição de pedido (quantidades por item) dentro do bloco e salva com PUT.
 */
function mostrarFormEditarPedido(bloco, idPedido, pedido) {
    const formDiv = bloco.querySelector(".form-editar-pedido");
    if (formDiv.style.display === "block") {
        formDiv.innerHTML = "";
        formDiv.style.display = "none";
        return;
    }
    formDiv.innerHTML = "";
    itensCardapio.forEach(function(item) {
        const qtd = (pedido.itens.find(function(i) { return i.id_item === item.id; }) || {}).quantidade || 0;
        const label = document.createElement("label");
        label.textContent = item.nome + " (qtd): ";
        const input = document.createElement("input");
        input.type = "number";
        input.min = 0;
        input.value = qtd;
        input.dataset.idItem = item.id;
        formDiv.appendChild(label);
        formDiv.appendChild(input);
        formDiv.appendChild(document.createElement("br"));
    });
    const btnSalvar = document.createElement("button");
    btnSalvar.type = "button";
    btnSalvar.textContent = "Salvar";
    btnSalvar.className = "btn-acao";
    const btnCancelar = document.createElement("button");
    btnCancelar.type = "button";
    btnCancelar.textContent = "Cancelar";
    btnCancelar.className = "btn-acao";
    formDiv.appendChild(btnSalvar);
    formDiv.appendChild(btnCancelar);
    formDiv.style.display = "block";

    btnSalvar.addEventListener("click", async function() {
        const inputs = formDiv.querySelectorAll("input[type=number]");
        const itens = [];
        inputs.forEach(function(input) {
            const qtd = parseInt(input.value, 10);
            if (qtd > 0) {
                itens.push({ id_item: parseInt(input.dataset.idItem, 10), quantidade: qtd });
            }
        });
        try {
            const res = await fetch("/api/pedidos/" + idPedido, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ itens: itens })
            });
            if (res.ok) {
                formDiv.innerHTML = "";
                formDiv.style.display = "none";
                carregarPedidos();
            } else {
                const data = await res.json();
                alert(data.erro || "Erro ao salvar.");
            }
        } catch (err) {
            alert("Erro de conexão.");
        }
    });
    btnCancelar.addEventListener("click", function() {
        formDiv.innerHTML = "";
        formDiv.style.display = "none";
    });
}

/**
 * Carrega o cardápio na página admin e preenche a lista com botões Editar e Excluir por item.
 */
async function carregarCardapioAdmin() {
    try {
        const res = await fetch("/api/cardapio");
        const itens = await res.json();
        const ul = document.getElementById("lista-itens-admin");
        ul.innerHTML = "";
        itens.forEach(function(item) {
            const li = document.createElement("li");
            li.className = "item-cardapio";
            li.dataset.id = item.id;
            li.innerHTML = "<span class=\"texto-item\">" + escapeHtml(item.nome) + " - R$ " + item.preco.toFixed(2) + "</span><span class=\"botoes-item\"><button type=\"button\" class=\"btn-editar-item\">Editar</button><button type=\"button\" class=\"btn-excluir-item\">Excluir</button></span>";
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
                const texto = li.querySelector(".texto-item").textContent;
                const idx = texto.lastIndexOf(" - R$ ");
                const nome = idx >= 0 ? texto.slice(0, idx) : texto;
                const preco = idx >= 0 ? texto.slice(idx + 6) : "0";
                mostrarFormEditarItem(li, id, nome, preco);
            });
        });
    } catch (err) {
        console.error("Erro ao carregar cardápio (admin):", err);
    }
}

function escapeHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
}

/**
 * Exclui um item do cardápio (DELETE /api/cardapio/:id) e recarrega a lista no admin.
 */
async function excluirItem(id) {
    try {
        const res = await fetch("/api/cardapio/" + id, { method: "DELETE" });
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

/**
 * Mostra formulário inline para editar nome e preço do item; Salvar envia PUT /api/cardapio/:id.
 */
function mostrarFormEditarItem(li, id, nomeAtual, precoAtual) {
    if (li.querySelector(".form-editar-item")) {
        return;
    }
    const textoEl = li.querySelector(".texto-item");
    const botoesEl = li.querySelector(".botoes-item");
    textoEl.style.display = "none";
    botoesEl.style.display = "none";
    const form = document.createElement("div");
    form.className = "form-editar-item";
    form.innerHTML = "<input type=\"text\" name=\"nome\" value=\"" + escapeHtml(nomeAtual) + "\" placeholder=\"Nome\"><input type=\"number\" name=\"preco\" step=\"0.01\" min=\"0\" value=\"" + precoAtual + "\" placeholder=\"Preço\"><button type=\"button\" class=\"btn-salvar-item\">Salvar</button><button type=\"button\" class=\"btn-cancelar-item\">Cancelar</button>";
    li.insertBefore(form, botoesEl);
    form.querySelector(".btn-salvar-item").addEventListener("click", async function() {
        const nome = form.querySelector("input[name=nome]").value.trim();
        const preco = parseFloat(form.querySelector("input[name=preco]").value);
        if (!nome || isNaN(preco)) {
            alert("Preencha nome e preço.");
            return;
        }
        try {
            const res = await fetch("/api/cardapio/" + id, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome: nome, preco: preco })
            });
            if (res.ok) {
                li.removeChild(form);
                textoEl.style.display = "";
                botoesEl.style.display = "";
                textoEl.textContent = nome + " - R$ " + preco.toFixed(2);
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

/**
 * Envia o novo item do formulário para a API (POST /api/cardapio) e atualiza a lista.
 */
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
        const res = await fetch("/api/cardapio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nome: nome, preco: preco })
        });
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
