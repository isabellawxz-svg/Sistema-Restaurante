async function carregarDashboardAdmin() {
    var painel = document.getElementById("painel-dashboard-admin");
    if (!painel) return;
    painel.innerHTML = "<p class=\"lista-vazia\">Carregando…</p>";
    var res = await apiFetch("/api/admin/dashboard");
    if (!res) return;
    var data = await res.json();
    if (!res.ok) {
        painel.innerHTML = "<p class=\"msg-erro\">" + (data.erro || "Erro ao carregar.") + "</p>";
        return;
    }
    var h = "<div class=\"dash-cards\">";
    h += "<div class=\"dash-card\"><h3>Comandas abertas</h3><p class=\"dash-valor\">" + data.comandas_abertas + "</p></div>";
    h += "<div class=\"dash-card\"><h3>Receita hoje</h3><p class=\"dash-valor\">R$ " + data.receita_hoje.toFixed(2) + "</p>";
    h += "<p class=\"dash-sub\">Comandas pagas com data de fechamento hoje</p></div>";
    h += "<div class=\"dash-card\"><h3>Insumos sem estoque</h3><p class=\"dash-valor dash-valor--alerta\">" + data.insumos_sem_estoque + "</p></div>";
    h += "<div class=\"dash-card\"><h3>Abaixo do mínimo</h3><p class=\"dash-valor dash-valor--alerta\">" + data.insumos_abaixo_minimo + "</p>";
    h += "<p class=\"dash-sub\">Estoque acima de zero mas ≤ mínimo configurado</p></div>";
    h += "</div>";
    painel.innerHTML = h;
}

document.addEventListener("DOMContentLoaded", function() {
    carregarDashboardAdmin();
});
