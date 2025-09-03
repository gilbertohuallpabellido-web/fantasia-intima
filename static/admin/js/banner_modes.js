(function(){
  function ready(fn){ if(document.readyState!='loading'){fn()} else {document.addEventListener('DOMContentLoaded',fn);} }
  ready(function(){
    const ids = ['id_opt_nueva','id_opt_ofertas','id_opt_link','id_opt_producto'];
    const campos = {
      enlace: document.querySelector('#id_enlace')?.closest('.form-row') || document.querySelector('#id_enlace')?.closest('div'),
      productos: document.querySelector('#id_productos_destacados')?.closest('.form-row') || document.querySelector('#id_productos_destacados')?.closest('div')
    };
    function exclusividad(clickedId){
      ids.forEach(id=>{
        if(id!==clickedId){
          const el=document.getElementById(id);
          if(el) el.checked=false;
        }
      });
    }
    function refrescarVisibilidad(){
      const m = modoActual();
      if(campos.enlace) campos.enlace.style.display = (m==='enlace')?'' : 'none';
      if(campos.productos) campos.productos.style.display = (m==='producto')?'' : 'none';
    }
    function modoActual(){
      if(document.getElementById('id_opt_nueva')?.checked) return 'nueva';
      if(document.getElementById('id_opt_ofertas')?.checked) return 'ofertas';
      if(document.getElementById('id_opt_link')?.checked) return 'enlace';
      if(document.getElementById('id_opt_producto')?.checked) return 'producto';
      return 'nueva';
    }
    ids.forEach(id=>{
      const el=document.getElementById(id); if(!el) return;
      el.addEventListener('change', e=>{ if(e.target.checked){ exclusividad(id); refrescarVisibilidad(); } else { refrescarVisibilidad(); } });
    });
    // Primera carga
    refrescarVisibilidad();
  });
})();
