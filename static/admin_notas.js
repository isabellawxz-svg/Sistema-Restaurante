var _insumosCache = [];

async function carregarInsumosParaNota() {
    var res = await apiFetch("/api/insumos");
    if (!res) return;
    _insumosCache = await res.json();
}

function htmlSelectInsumo(selectedId) {
    var h = "<select class=\"nota-sel-insumo\">";
    h += "<option value=\"\">— insumo —</option>";
    _insumosCache.forEach(function(i) {
        h += "<option value=\"" + i.id + "\"" + (String(selectedId) === String(i.id) ? " selected" : "") + ">" +
            escapeHtml(i.nome) + "</option>";
    });
    h += "</select>";
    return h;
}

function addLinhaNota() {
    var wrap = document.getElementById("nota-itens-linhas");
    var row = document.createElement("div");
    row.className = "nota-linha";
    row.innerHTML = htmlSelectInsumo("") +
        " Qtd <input type=\"number\" class=\"nota-qtd\" step=\"0.0001\" min=\"0\" value=\"1\">" +
        " V.unit. <input type=\"number\" class=\"nota-vu\" step=\"0.01\" min=\"0\" value=\"0\">";
    wrap.appendChild(row);
}

async function carregarListaNotas() {
    var div = document.getElementById("lista-notas");
    if (!div) return;
    var res = await apiFetch("/api/notas-compra");
    if (!res) return;
    var lista = await res.json();
    if (lista.length === 0) {
        div.innerHTML = "<p class=\"lista-vazia\">Nenhuma nota.</p>";
        return;
    }
    var tbl = "<table class=\"tabela-admin\"><thead><tr><th>Data</th><th>Fornecedor</th><th>Nº</th><th>Valor</th></tr></thead><tbody>";
    lista.forEach(function(n) {
        tbl += "<tr><td>" + escapeHtml(n.data_nota || n.criado_em) + "</td><td>" + escapeHtml(n.fornecedor) + "</td><td>" +
            escapeHtml(n.numero_nota) + "</td><td>R$ " + n.valor_total.toFixed(2) + "</td></tr>";
    });
    tbl += "</tbody></table>";
    div.innerHTML = tbl;
}

document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("form-nota");
    if (!form) return;
    carregarInsumosParaNota().then(function() {
        addLinhaNota();
        carregarListaNotas();
    });
    document.getElementById("btn-nota-add-linha").addEventListener("click", addLinhaNota);
    form.addEventListener("submit", async function(ev) {
        ev.preventDefault();
        var msg = document.getElementById("msg-notas");
        var itens = [];
        document.querySelectorAll("#nota-itens-linhas .nota-linha").forEach(function(row) {
            var sid = row.querySelector(".nota-sel-insumo").value;
            var q = parseFloat(row.querySelector(".nota-qtd").value);
            var vu = parseFloat(row.querySelector(".nota-vu").value);
            if (sid && q > 0) itens.push({ id_insumo: parseInt(sid, 10), quantidade: q, valor_unitario: isNaN(vu) ? 0 : vu });
        });
        if (itens.length === 0) {
            msg.textContent = "Inclua ao menos uma linha com insumo e quantidade.";
            return;
        }
        var res = await apiFetch("/api/notas-compra", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                fornecedor: document.getElementById("nota-fornecedor").value.trim(),
                numero_nota: document.getElementById("nota-numero").value.trim(),
                data_nota: document.getElementById("nota-data").value,
                observacao: document.getElementById("nota-obs").value.trim(),
                itens: itens
            })
        });
        if (!res) return;
        var data = await res.json();
        if (res.ok) {
            msg.textContent = "Nota registrada e estoque atualizado.";
            form.reset();
            document.getElementById("nota-itens-linhas").innerHTML = "";
            addLinhaNota();
            carregarListaNotas();
            carregarInsumosParaNota();
        } else {
            msg.textContent = data.erro || "Erro.";
        }
    });
});
