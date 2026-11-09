// 選單開合
const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('nav');
toggle?.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') === 'true';
  toggle.setAttribute('aria-expanded', String(!open));
  nav.classList.toggle('open', !open);
});

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
