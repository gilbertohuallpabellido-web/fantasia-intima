(function(){
    function ready(fn){ if(document.readyState!='loading'){fn();} else {document.addEventListener('DOMContentLoaded',fn);} }
    ready(function(){
        const chk = document.getElementById('id_es_oferta');
    const precioInput = document.getElementById('id_precio_oferta');
    const precioOfertaRow = precioInput?.closest('.form-row, div.field-precio_oferta, .form-group');
    if(!chk || !precioOfertaRow || !precioInput) return;

        function sync(){
            if(chk.checked){
                precioOfertaRow.style.opacity = '1';
                precioOfertaRow.style.transition = 'all .25s';
                precioOfertaRow.classList.add('oferta-activa');
                precioInput.removeAttribute('disabled');
            } else {
                precioOfertaRow.style.opacity = '0.4';
                precioOfertaRow.classList.remove('oferta-activa');
                // Deshabilita y limpia el valor para evitar confusión
                precioInput.value = '';
                precioInput.setAttribute('disabled','disabled');
            }
        }
        chk.addEventListener('change', sync);
        sync();

        // Estilos inyectados
        const style = document.createElement('style');
        style.textContent = `
            .oferta-activa input { border-color: #dc2626 !important; box-shadow: 0 0 0 1px #dc262633; }
            .oferta-activa label:after { content: ' (OFERTA)'; color:#dc2626; font-weight:600; }
        `;
        document.head.appendChild(style);
    });
})();
