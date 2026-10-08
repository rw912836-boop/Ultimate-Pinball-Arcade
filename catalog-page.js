(() => {
  const body = document.body;
  const file = body.dataset.catalog;
  const condition = body.dataset.condition;
  const grid = document.getElementById('product-grid');
  const count = document.getElementById('result-count');
  const search = document.getElementById('catalog-search');
  const sort = document.getElementById('catalog-sort');
  const stock = document.getElementById('catalog-stock');
  const pager = document.getElementById('pagination');
  const perPage = 24;
  let all = [];
  let page = 1;

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const usd = (value) => value == null ? 'Ask for price' : `$${Number(value).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} USD`;
  const availabilityText = (value) => value === 'sold-out' ? 'Sold out' : value === 'on-demand' ? 'On demand' : 'Available';
  const priceLabel = (product) => product.priceCurrency === "USD" ? "Listed price - USD" : "Converted from EUR - USD estimate";
  const priceDisclaimer = (product) => product.priceCurrency === "USD" ? "This listing price was provided in USD. Contact us to confirm the current price and availability before ordering." : "USD price is converted from the source listing. Confirm the current price, condition, and availability before ordering.";

  function card(product, index) {
    const images = product.images || [];
    const main = images[0] || '';
    const title = escapeHtml(product.title);
    const imageAlt = `${title} pinball machine`;
    const thumbnails = images.slice(1).map((src) => `<button type="button" aria-label="Show another photo of ${title}" data-image="${escapeHtml(src)}"><img src="${escapeHtml(src)}" alt="" loading="lazy"></button>`).join('');
    const oldPrice = product.regularPriceUsd && product.priceUsd && product.regularPriceUsd > product.priceUsd
      ? `<span class="previous-price">${usd(product.regularPriceUsd)}</span>` : '';
    const stockClass = product.availability === 'sold-out' ? ' sold-out' : '';
    const sku = product.sku ? ` · ${escapeHtml(product.sku)}` : '';
    const excerpt = product.description ? `<p>${escapeHtml(product.description)}</p>` : '<p>Product description is not available yet. Contact us to confirm machine details.</p>';
    const gallery = thumbnails ? `<p class="detail-caption">More product photos are shown below the main image.</p>` : '';
    const subject = encodeURIComponent(`Availability inquiry: ${product.title}`);
    return `<article class="catalog-card" data-index="${index}">
      <div class="machine-photo"><span class="condition-badge">${condition === 'new' ? 'New machine' : 'Used machine'}</span><span class="stock-badge${stockClass}">${availabilityText(product.availability)}</span>${main ? `<img class="main-product-image" src="${escapeHtml(main)}" alt="${imageAlt}" loading="lazy" onerror="this.style.display='none'">` : '<span>Photo coming soon</span>'}</div>
      ${thumbnails ? `<div class="thumbnails" aria-label="Additional machine photos">${thumbnails}</div>` : ''}
      <div class="machine-info"><h2 class="machine-title">${title}</h2><div class="sku">${condition === 'new' ? 'New pinball' : 'Used pinball'}${sku}</div><div class="machine-price">${usd(product.priceUsd)}${oldPrice}<br><small>${priceLabel(product)}</small></div>
      <div class="machine-actions"><a href="mailto:info@ultimatepinballarcade.com?subject=${subject}">Ask about machine</a><details class="details"><summary>Details</summary><div class="details-panel">${excerpt}${product.availability === 'sold-out' ? '<p><strong>Listed as sold out. Please contact us to check current availability.</strong></p>' : ''}${gallery}<p>USD price is converted from the source listing. Confirm the current price, condition, and availability with us before ordering.</p></div></details></div></div></article>`;
  }

  function draw() {
    const term = search.value.trim().toLowerCase();
    let items = all.filter((p) => {
      const matchesText = !term || `${p.title} ${p.sku} ${p.description}`.toLowerCase().includes(term);
      const matchesStock = stock.value === 'all' || p.availability === stock.value;
      return matchesText && matchesStock;
    });
    if (sort.value === 'title') items.sort((a,b) => a.title.localeCompare(b.title));
    if (sort.value === 'price-asc') items.sort((a,b) => (a.priceUsd ?? Infinity) - (b.priceUsd ?? Infinity));
    if (sort.value === 'price-desc') items.sort((a,b) => (b.priceUsd ?? -Infinity) - (a.priceUsd ?? -Infinity));
    const totalPages = Math.max(1, Math.ceil(items.length / perPage));
    page = Math.min(page, totalPages);
    const slice = items.slice((page - 1) * perPage, page * perPage);
    count.textContent = `Showing ${items.length ? (page - 1) * perPage + 1 : 0}–${Math.min(page * perPage, items.length)} of ${items.length} ${condition} machines`;
    grid.innerHTML = slice.length ? slice.map(card).join('') : '<div class="empty">No machines match those filters. Try a different search.</div>';
    pager.innerHTML = totalPages > 1 ? Array.from({length:totalPages},(_,i)=>`<button class="page-button${page===i+1?' active':''}" type="button" aria-label="Page ${i+1}" ${page===i+1?'aria-current="page"':''} onclick="upaPage(${i+1})">${i+1}</button>`).join('') : '';
  }

  window.upaPage = (next) => { page = next; draw(); document.getElementById('catalog').scrollIntoView({behavior:'smooth'}); };
  grid.addEventListener('click', (event) => { const button = event.target.closest('.thumbnails button'); if (!button) return; const img = button.closest('.catalog-card').querySelector('.main-product-image'); if (img) { img.src = button.dataset.image; img.style.display = ''; } });
  [search, sort, stock].forEach((control) => control.addEventListener('input', () => { page = 1; draw(); }));

  fetch(file).then((response) => { if (!response.ok) throw new Error('Catalog unavailable'); return response.json(); }).then((data) => {
    all = Array.isArray(data.products) ? data.products : [];
    const hero = document.getElementById('hero-art');
    if (hero && all[0]?.images?.[0]) hero.src = all[0].images[0];
    const rate = Number(data.exchangeRate).toFixed(4);
    document.getElementById('currency-note').textContent = `Supplier prices are converted from EUR to USD at 1 EUR = $${rate} (ECB reference rate, ${data.rateDate}). Rocky Pinball Machine is shown at its provided USD price. Prices, machine condition, and availability can change; contact us to confirm before ordering.`;
    document.getElementById('catalog-total').textContent = `${all.length} ${condition} machines`;
    draw();
  }).catch(() => { grid.innerHTML = '<div class="load-error">We could not load the machine catalog just now. Please refresh this page or contact us for help.</div>'; });
})();
