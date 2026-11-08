
// DESENHAR AS BARRAS DOS RELATÓRIOS

document.addEventListener("DOMContentLoaded", function () {

    const barras = document.querySelectorAll("[data-width]");

    barras.forEach(function (barra) {

        const valor = Number(barra.dataset.width);

        if (Number.isFinite(valor)) {
            const largura = Math.max(0, Math.min(100, valor));

            barra.style.width = largura + "%";
        }

    });

});
