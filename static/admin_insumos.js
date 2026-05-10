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
    var tbl = "<table class=\"tabela-admin\"><thead><tr><th>Nome</th><th>Unidade</th><th>Estoque</th><th>Mínimo</th><th>Status</th></tr></thead><tbody>";
    lista.forEach(function(i) {
        var statusHtml = "";
        if (i.estoque_atual <= 0) {
            statusHtml = "<span class=\"badge-estoque badge-estoque-critico\">Sem estoque</span>";
        } else if (i.estoque_minimo > 0 && i.estoque_atual <= i.estoque_minimo) {
            statusHtml = "<span class=\"badge-estoque badge-estoque-alerta\">Abaixo do mínimo</span>";
        } else {
            statusHtml = "<span class=\"badge-estoque badge-estoque-ok\">OK</span>";
        }
        var trClass = i.alerta_estoque ? " linha-estoque-alerta" : "";
        tbl += "<tr class=\"" + trClass.trim() + "\"><td>" + escapeHtml(i.nome) + "</td><td>" + escapeHtml(i.unidade) + "</td><td>" +
            i.estoque_atual + "</td><td>" + i.estoque_minimo + "</td><td>" + statusHtml + "</td></tr>";
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
        var estMin = parseFloat(document.getElementById("insumo-minimo").value);
        if (!nome) {
            msg.textContent = "Informe o nome.";
            return;
        }
        var res = await apiFetch("/api/insumos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: nome,
                unidade: unidade,
                estoque_atual: isNaN(est) ? 0 : est,
                estoque_minimo: isNaN(estMin) ? 0 : Math.max(0, estMin)
            })
        });
        if (!res) return;
        var data = await res.json();
        if (res.ok) {
            msg.textContent = "Insumo cadastrado.";
            form.reset();
            document.getElementById("insumo-unidade").value = "un";
            document.getElementById("insumo-minimo").value = "0";
            carregarListaInsumos();
        } else {
            msg.textContent = data.erro || "Erro.";
        }
    });
});
