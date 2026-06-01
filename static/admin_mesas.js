async function carregarMesasAdmin() {
    var div = document.getElementById("lista-mesas-admin");
    if (!div) return;
    var res = await apiFetch("/api/mesas");
    if (!res) return;
    var lista = await res.json();
    if (!res.ok) {
        div.innerHTML = "<p class=\"msg-erro\">" + escapeHtml(lista.erro || "Erro.") + "</p>";
        return;
    }
    div.innerHTML = "";
    if (lista.length === 0) {
        div.innerHTML = "<p class=\"lista-vazia\">Nenhuma mesa cadastrada.</p>";
        return;
    }
    var tbl = "<table class=\"tabela-admin\"><thead><tr><th>Nº</th><th>Capacidade</th><th>Status</th><th>Comanda</th><th>Ações</th></tr></thead><tbody>";
    lista.forEach(function(m) {
        var comandaTxt = m.comanda ? "#" + m.comanda.id + " (R$ " + Number(m.comanda.total).toFixed(2) + ")" : "—";
        var selStatus = "<select class=\"mesa-edit-status\" data-id=\"" + m.id + "\">";
        ["livre", "reservada"].forEach(function(s) {
            if (m.status === "ocupada" && s !== "livre") {
                return;
            }
            selStatus += "<option value=\"" + s + "\"" + (m.status === s ? " selected" : "") + ">" +
                (s === "livre" ? "Livre" : "Reservada") + "</option>";
        });
        if (m.status === "ocupada") {
            selStatus = "<span class=\"badge badge-comanda-aberta\">Ocupada</span>";
        }
        tbl += "<tr><td>" + escapeHtml(m.numero) + "</td><td>" +
            "<input type=\"number\" min=\"1\" class=\"mesa-edit-cap\" data-id=\"" + m.id + "\" value=\"" + m.capacidade + "\" style=\"width:4rem\"></td><td>" +
            selStatus + "</td><td>" + comandaTxt + "</td><td>";
        if (!m.id_comanda_ativa) {
            tbl += "<button type=\"button\" class=\"btn-secundario btn-salvar-mesa\" data-id=\"" + m.id + "\">Salvar</button> " +
                "<button type=\"button\" class=\"btn-excluir-mesa\" data-id=\"" + m.id + "\">Excluir</button>";
        } else {
            tbl += "<span class=\"meta-linha\">Feche a comanda no caixa</span>";
        }
        tbl += "</td></tr>";
    });
    tbl += "</tbody></table>";
    div.innerHTML = tbl;

    div.querySelectorAll(".btn-salvar-mesa").forEach(function(btn) {
        btn.addEventListener("click", function() {
            salvarMesaAdmin(parseInt(btn.getAttribute("data-id"), 10));
        });
    });
    div.querySelectorAll(".btn-excluir-mesa").forEach(function(btn) {
        btn.addEventListener("click", function() {
            excluirMesaAdmin(parseInt(btn.getAttribute("data-id"), 10));
        });
    });
}

async function salvarMesaAdmin(id) {
    var msg = document.getElementById("msg-mesas-admin");
    var capEl = document.querySelector(".mesa-edit-cap[data-id=\"" + id + "\"]");
    var statusEl = document.querySelector(".mesa-edit-status[data-id=\"" + id + "\"]");
    var body = { capacidade: parseInt(capEl.value, 10) };
    if (statusEl) {
        body.status = statusEl.value;
    }
    var res = await apiFetch("/api/mesas/" + id, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    if (!res) return;
    var data = await res.json();
    if (res.ok) {
        msg.textContent = "Mesa atualizada.";
        carregarMesasAdmin();
    } else {
        msg.textContent = data.erro || "Erro ao salvar.";
    }
}

async function excluirMesaAdmin(id) {
    if (!confirm("Excluir esta mesa?")) return;
    var msg = document.getElementById("msg-mesas-admin");
    var res = await apiFetch("/api/mesas/" + id, { method: "DELETE" });
    if (!res) return;
    var data = await res.json();
    if (res.ok) {
        msg.textContent = data.mensagem || "Mesa excluída.";
        carregarMesasAdmin();
    } else {
        msg.textContent = data.erro || "Erro ao excluir.";
    }
}

document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("form-mesa-admin");
    if (!form) return;
    carregarMesasAdmin();
    form.addEventListener("submit", async function(ev) {
        ev.preventDefault();
        var msg = document.getElementById("msg-mesas-admin");
        var numero = document.getElementById("mesa-numero").value.trim();
        var cap = parseInt(document.getElementById("mesa-capacidade").value, 10);
        var status = document.getElementById("mesa-status-nova").value;
        if (!numero) {
            msg.textContent = "Informe o número da mesa.";
            return;
        }
        var res = await apiFetch("/api/mesas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ numero: numero, capacidade: cap, status: status })
        });
        if (!res) return;
        var data = await res.json();
        if (res.ok) {
            msg.textContent = "Mesa cadastrada.";
            form.reset();
            document.getElementById("mesa-capacidade").value = "4";
            carregarMesasAdmin();
        } else {
            msg.textContent = data.erro || "Erro.";
        }
    });
});
