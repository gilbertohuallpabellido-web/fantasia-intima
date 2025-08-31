(function () {
  function ready(fn){ document.readyState!=='loading'?fn():document.addEventListener('DOMContentLoaded',fn); }
  function showSkeleton(on){
    const s = document.getElementById('list-skeleton');
    const list = document.getElementById('product-list');
    if(!s || !list) return;
    if(on){ s.classList.remove('hidden'); list.classList.add('hidden'); }
    else { s.classList.add('hidden'); list.classList.remove('hidden'); }
  }
  function fetchReplace(url){
    showSkeleton(true);
    fetch(url, { headers:{'X-Requested-With':'fetch'} })
      .then(r=>r.text())
      .then(html=>{
        const doc = new DOMParser().parseFromString(html,'text/html');
        const newList = doc.getElementById('product-list');
        if(!newList){ window.location.href=url; return; }
        document.getElementById('product-list').innerHTML = newList.innerHTML;
        const section = document.getElementById('product-list-section');
        window.history.pushState({},'',url.replace('#product-list-section',''));
        section.scrollIntoView({behavior:'smooth',block:'start'});
      })
      .catch(()=>window.location.href=url)
      .finally(()=>showSkeleton(false));
  }
  function applyParamAndFetch(mutator){
    const u = new URL(window.location.href);
    mutator(u);
    fetchReplace(u.toString() + '#product-list-section');
  }

  ready(function(){
    const sort = document.getElementById('sort-by');
    if(sort){
      sort.addEventListener('change', function(){
        applyParamAndFetch(u=>{
          if(this.value==='default'){ u.searchParams.delete('orden'); }
          else { u.searchParams.set('orden', this.value); }
          u.searchParams.delete('page');
        });
      });
    }

    ['price-form','color-form'].forEach(id=>{
      const f = document.getElementById(id);
      if(!f) return;
      f.addEventListener('submit', function(e){
        e.preventDefault();
        const data = new FormData(this);
        applyParamAndFetch(u=>{
          for(const [k,v] of data.entries()){
            if(!v) u.searchParams.delete(k);
            else u.searchParams.set(k, v);
          }
          u.searchParams.delete('page');
        });
      });
    });
  });
})();