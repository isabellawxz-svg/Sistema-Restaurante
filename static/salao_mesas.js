/**
 * Mapa visual de mesas no salão e no caixa.
 * Depende de: apiFetch, escapeHtml, abrirModalNovaComanda, abrirModalLancamentoComanda, carregarComandas
 */

var LABEL_STATUS_MESA = {
    livre: "Livre",
    ocupada: "Ocupada",
    reservada: "Reservada"
};

async function carregarMapaMesas() {
    var root = document.getElementById("mapa-mesas");
    if (!root) return;
    var res = await apiFetch("/api/mesas");
    if (!res) return;
    var mesas = await res.json();
    if (!res.ok) {
        root.innerHTML = "<p class=\"msg-erro\">" + escapeHtml((mesas && mesas.erro) || "Erro ao carregar mesas.") + "</p>";
        return;
    }
    if (mesas.length === 0) {
        root.innerHTML = "<p class=\"lista-vazia\">Nenhuma mesa cadastrada. O admin pode cadastrar em <strong>Mesas do salão</strong>.</p>";
        return;
    }
    var html = "<div class=\"mapa-mesas-legenda\">" +
        "<span class=\"legenda-item\"><span class=\"legenda-cor mesa-cor-livre\"></span> Livre</span>" +
        "<span class=\"legenda-item\"><span class=\"legenda-cor mesa-cor-ocupada\"></span> Ocupada</span>" +
        "<span class=\"legenda-item\"><span class=\"legenda-cor mesa-cor-reservada\"></span> Reservada</span>" +
        "</div><div class=\"mapa-mesas-grid\">";
    mesas.forEach(function(m) {
        var st = m.status || "livre";
        var titulo = "Mesa " + escapeHtml(m.numero);
        var sub = escapeHtml(LABEL_STATUS_MESA[st] || st) + " · " + m.capacidade + " lugares";
        if (m.comanda) {
            sub += "<br>Comanda #" + m.comanda.id;
            if (m.comanda.cliente_nome) {
                sub += " · " + escapeHtml(m.comanda.cliente_nome);
            }
            sub += "<br><strong>R$ " + Number(m.comanda.total).toFixed(2) + "</strong>";
            if (m.comanda.itens_count > 0) {
                sub += " · " + m.comanda.itens_count + " item(ns)";
            }
        }
        html += "<button type=\"button\" class=\"mesa-card mesa-card--" + st + "\" data-mesa-id=\"" + m.id + "\" " +
            "data-mesa-numero=\"" + escapeHtml(m.numero) + "\" data-mesa-status=\"" + st + "\" " +
            "data-comanda-id=\"" + (m.id_comanda_ativa || "") + "\" title=\"" + titulo + "\">" +
            "<span class=\"mesa-card-numero\">" + escapeHtml(m.numero) + "</span>" +
            "<span class=\"mesa-card-meta\">" + sub + "</span></button>";
    });
    html += "</div>";
    root.innerHTML = html;
    root.querySelectorAll(".mesa-card").forEach(function(btn) {
        btn.addEventListener("click", function() {
            tratarCliqueMesa(btn);
        });
    });
}

function tratarCliqueMesa(btn) {
    var status = btn.getAttribute("data-mesa-status");
    var idMesa = parseInt(btn.getAttribute("data-mesa-id"), 10);
    var numero = btn.getAttribute("data-mesa-numero");
    var idComanda = btn.getAttribute("data-comanda-id");
    if (status === "reservada") {
        alert("Mesa " + numero + " está reservada. Altere o status no cadastro de mesas (admin).");
        return;
    }
    if (status === "ocupada" && idComanda) {
        if (typeof abrirModalLancamentoComanda === "function") {
            abrirModalLancamentoComanda(parseInt(idComanda, 10));
        }
        return;
    }
    if (status === "livre") {
        if (typeof abrirModalNovaComanda === "function") {
            abrirModalNovaComanda({ id_mesa: idMesa, mesaNumero: numero });
        }
    }
}
