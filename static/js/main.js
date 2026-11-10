// 選單開合
const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('nav');
toggle?.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') === 'true';
  toggle.setAttribute('aria-expanded', String(!open));
  nav.classList.toggle('open', !open);
});

// 區域下拉選單（歐洲 → 國家）
const drops = document.querySelectorAll('.nav-drop');
const closeDrops = (except) => drops.forEach((d) => {
  if (d !== except) { d.classList.remove('open'); d.querySelector('.nav-drop-btn').setAttribute('aria-expanded', 'false'); }
});
drops.forEach((d) => {
  const btn = d.querySelector('.nav-drop-btn');
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = d.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
    closeDrops(d);
  });
});
document.addEventListener('click', (e) => { if (!e.target.closest('.nav-drop')) closeDrops(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrops(); });

// 圖片放大
const lb = document.querySelector('.lightbox');
const lbImg = lb?.querySelector('img');
document.querySelectorAll('.fig .zoom').forEach((btn) => {
  btn.addEventListener('click', () => {
    const img = btn.querySelector('img');
    lbImg.src = img.currentSrc || img.src;
    lbImg.alt = img.alt;
    lb.hidden = false;
    lb.querySelector('.lb-close').focus();
  });
});
const closeLb = () => { if (lb) lb.hidden = true; };
lb?.addEventListener('click', closeLb);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLb(); });
