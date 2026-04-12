async function carregarListaInsumos() {
    var div = document.getElementById("lista-insumos");
    if (!div) return;
    var res = await apiFetch("/api/insumos");
    if (!res) return;
    var lista = await res.json();
    div.innerHTML = "";
    if (lista.length === 0) {
        div.innerHTML = "<p class=\"lista-vazia\">Nenhum insumo cadastrado.</p>";
        return;
    }
    var tbl = "<table class=\"tabela-admin\"><thead><tr><th>Nome</th><th>Unidade</th><th>Estoque</th></tr></thead><tbody>";
    lista.forEach(function(i) {
        tbl += "<tr><td>" + escapeHtml(i.nome) + "</td><td>" + escapeHtml(i.unidade) + "</td><td>" + i.estoque_atual + "</td></tr>";
    });
    tbl += "</tbody></table>";
    div.innerHTML = tbl;
}

document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("form-insumo");
    if (!form) return;
    carregarListaInsumos();
    form.addEventListener("submit", async function(ev) {
        ev.preventDefault();
        var msg = document.getElementById("msg-insumos");
        var nome = document.getElementById("insumo-nome").value.trim();
        var unidade = document.getElementById("insumo-unidade").value.trim() || "un";
        var est = parseFloat(document.getElementById("insumo-estoque").value);
        if (!nome) {
            msg.textContent = "Informe o nome.";
            return;
        }
        var res = await apiFetch("/api/insumos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nome: nome, unidade: unidade, estoque_atual: isNaN(est) ? 0 : est })
        });
        if (!res) return;
        var data = await res.json();
        if (res.ok) {
            msg.textContent = "Insumo cadastrado.";
            form.reset();
            document.getElementById("insumo-unidade").value = "un";
            carregarListaInsumos();
        } else {
            msg.textContent = data.erro || "Erro.";
        }
    });
});
