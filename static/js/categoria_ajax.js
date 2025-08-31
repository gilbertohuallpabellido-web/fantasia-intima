(function () {
  function onReady(fn){ document.readyState!=='loading'?fn():document.addEventListener('DOMContentLoaded', fn); }
  function showSkeleton(on){
    const s = document.getElementById('list-skeleton');
    const list = document.getElementById('product-list');
    if(!s || !list) return;
    if(on){ s.classList.remove('hidden'); list.classList.add('hidden'); }
    else { s.classList.add('hidden'); list.classList.remove('hidden'); }
  }
  onReady(function () {
    const listSection = document.getElementById('product-list-section');
    if (!listSection) return;

    function attachHandlers(root = document) {
      root.querySelectorAll('a.js-category-link').forEach((a) => {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          const url = this.href;

          showSkeleton(true);
          fetch(url, { headers: { 'X-Requested-With': 'fetch' } })
            .then((r) => r.text())
            .then((html) => {
              const parser = new DOMParser();
              const doc = parser.parseFromString(html, 'text/html');
              const newSection = doc.getElementById('product-list-section');
              if (!newSection) { window.location.href = url; return; }
              listSection.innerHTML = newSection.innerHTML;
              const cleanUrl = url.replace('#product-list-section', '');
              window.history.pushState({}, '', cleanUrl);
              listSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
              attachHandlers(listSection);
            })
            .catch(() => { window.location.href = url; })
            .finally(()=> showSkeleton(false));
        });
      });
    }

    attachHandlers();
    window.addEventListener('popstate', function () {
      fetch(window.location.href, { headers: { 'X-Requested-With': 'fetch' } })
        .then((r) => r.text())
        .then((html) => {
          const parser = new DOMParser();
          const doc = parser.parseFromString(html, 'text/html');
          const newSection = doc.getElementById('product-list-section');
          if (newSection) {
            listSection.innerHTML = newSection.innerHTML;
            attachHandlers(listSection);
          }
        })
        .catch(() => {});
    });
  });
})();