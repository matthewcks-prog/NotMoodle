// Render credits donut with Chart.js, fallback to SVG if Chart.js missing
function renderCreditsDonut(canvasId, earned, required, color = '#6787d6') {
  const el = document.getElementById(canvasId);
  const remaining = Math.max(0, required - earned);
  if (window.Chart) {
    new Chart(el.getContext('2d'), {
      type: 'doughnut',
      data: { datasets: [{ data: [earned, remaining], backgroundColor: [color, '#e5e7eb'], borderWidth: 0 }] },
      options: { cutout: '68%', plugins: { legend: { display: false }, tooltip: { enabled: false } } }
    });
    // Center label
    const txt = el.nextElementSibling; // creditsText div in template
    if (txt && typeof earned === 'number') txt.textContent = `${earned} / ${required} credits`;
    return;
  }
  // Fallback SVG
  const R = 70, C = 2 * Math.PI * R; const pct = required ? (earned / required) : 0;
  el.replaceWith(Object.assign(document.createElementNS('http://www.w3.org/2000/svg', 'svg'), {
    id: canvasId, setAttribute: function() {}, innerHTML:
    `<circle cx="90" cy="90" r="${R}" stroke="#e5e7eb" stroke-width="18" fill="none" />
     <circle cx="90" cy="90" r="${R}" stroke="${color}" stroke-width="18" fill="none"
             stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct)}" stroke-linecap="round"/>
     <text x="90" y="95" text-anchor="middle" font-size="18" font-weight="700">${earned}/${required}</text>`
  }));
}