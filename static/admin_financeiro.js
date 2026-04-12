function _hojeISO() {
    var d = new Date();
    return d.toISOString().slice(0, 10);
}

function _trintaDiasAtras() {
    var d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
}

function renderPainelFinanceiro(data) {
    var el = document.getElementById("painel-financeiro");
    if (!el) return;
    var h = "<div class=\"fin-cards\">";
    h += "<div class=\"fin-card\"><h3>Receita (vendas)</h3><p class=\"fin-valor\">R$ " + data.receita_vendas.toFixed(2) + "</p>";
    h += "<p class=\"fin-sub\">" + data.comandas_fechadas + " comandas no período</p></div>";
    h += "<div class=\"fin-card\"><h3>Compras registradas</h3><p class=\"fin-valor\">R$ " + data.compras_registradas_valor.toFixed(2) + "</p>";
    h += "<p class=\"fin-sub\">Soma das notas de compra (lançamento manual)</p></div></div>";
    h += "<h3 class=\"fin-titulo-sec\">Por forma de pagamento</h3><ul class=\"fin-lista-forma\">";
    (data.por_forma_pagamento || []).forEach(function(l) {
        var nome = { dinheiro: "Dinheiro", pix: "PIX", cartao: "Cartão" }[l.forma_pagamento] || l.forma_pagamento;
        h += "<li><strong>" + nome + "</strong>: R$ " + l.total.toFixed(2) + " (" + l.comandas + " comandas)</li>";
    });
    h += "</ul><p class=\"fin-periodo\">Período: " + data.inicio + " a " + data.fim + "</p>";
    el.innerHTML = h;
}

async function atualizarPainelFinanceiro() {
    var ini = document.getElementById("fin-inicio").value || _trintaDiasAtras();
    var fim = document.getElementById("fin-fim").value || _hojeISO();
    var res = await apiFetch("/api/financeiro/resumo?inicio=" + encodeURIComponent(ini) + "&fim=" + encodeURIComponent(fim));
    if (!res) return;
    var data = await res.json();
    if (!res.ok) {
        document.getElementById("painel-financeiro").innerHTML = "<p class=\"msg-erro\">" + (data.erro || "Erro ao carregar.") + "</p>";
        return;
    }
    renderPainelFinanceiro(data);
}

document.addEventListener("DOMContentLoaded", function() {
    var btn = document.getElementById("btn-fin-atualizar");
    if (!btn) return;
    document.getElementById("fin-fim").value = _hojeISO();
    document.getElementById("fin-inicio").value = _trintaDiasAtras();
    btn.addEventListener("click", atualizarPainelFinanceiro);
    atualizarPainelFinanceiro();
});
