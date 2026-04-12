var _receitaItemId = null;

async function popularSelectCardapio() {
    var sel = document.getElementById("receita-item-cardapio");
    if (!sel) return;
    var res = await apiFetch("/api/cardapio");
    if (!res) return;
    var itens = await res.json();
    sel.innerHTML = "";
    itens.forEach(function(it) {
        var o = document.createElement("option");
        o.value = it.id;
        o.textContent = it.nome + " — R$ " + it.preco.toFixed(2);
        sel.appendChild(o);
    });
}

function addLinhaReceita(idInsumo, qtd) {
    var wrap = document.getElementById("receita-linhas");
    var row = document.createElement("div");
    row.className = "receita-linha";
    var h = "";
    h += "<select class=\"rec-sel-insumo\">";
    h += "<option value=\"\">— insumo —</option>";
    window._insumosReceita.forEach(function(i) {
        h += "<option value=\"" + i.id + "\"" + (String(idInsumo) === String(i.id) ? " selected" : "") + ">" +
            escapeHtml(i.nome) + " (" + escapeHtml(i.unidade) + ")</option>";
    });
    h += "</select>";
    h += " por 1 unidade vendida: <input type=\"number\" class=\"rec-qtd\" step=\"0.0001\" min=\"0\" value=\"" + (qtd || 0) + "\">";
    row.innerHTML = h;
    wrap.appendChild(row);
}

async function carregarReceitaAtual() {
    var sel = document.getElementById("receita-item-cardapio");
    var wrap = document.getElementById("receita-linhas");
    var msg = document.getElementById("msg-receitas");
    msg.textContent = "";
    _receitaItemId = parseInt(sel.value, 10);
    var res = await apiFetch("/api/cardapio/" + _receitaItemId + "/composicao");
    if (!res) return;
    var data = await res.json();
    wrap.innerHTML = "";
    if (!data.itens || data.itens.length === 0) {
        addLinhaReceita("", 0);
        return;
    }
    data.itens.forEach(function(l) {
        addLinhaReceita(l.id_insumo, l.quantidade);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    var wrap = document.getElementById("receita-linhas");
    if (!wrap) return;
    apiFetch("/api/insumos").then(function(res) {
        if (!res) return;
        return res.json();
    }).then(function(ins) {
        window._insumosReceita = ins || [];
        return popularSelectCardapio();
    }).then(function() {
        document.getElementById("btn-receita-carregar").addEventListener("click", carregarReceitaAtual);
        document.getElementById("btn-receita-add").addEventListener("click", function() { addLinhaReceita("", 0); });
        document.getElementById("btn-receita-salvar").addEventListener("click", async function() {
            var msg = document.getElementById("msg-receitas");
            var idItem = parseInt(document.getElementById("receita-item-cardapio").value, 10);
            var itens = [];
            document.querySelectorAll("#receita-linhas .receita-linha").forEach(function(row) {
                var sid = row.querySelector(".rec-sel-insumo").value;
                var q = parseFloat(row.querySelector(".rec-qtd").value);
                if (sid && q > 0) itens.push({ id_insumo: parseInt(sid, 10), quantidade: q });
            });
            var res = await apiFetch("/api/cardapio/" + idItem + "/composicao", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ itens: itens })
            });
            if (!res) return;
            var data = await res.json();
            if (res.ok) {
                msg.textContent = "Receita salva (" + (data.itens && data.itens.length) + " insumos).";
            } else {
                msg.textContent = data.erro || "Erro.";
            }
        });
    });
});
