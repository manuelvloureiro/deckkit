// Arrow keys, space, Page Up/Down or a click move through the slides. The address keeps the
// slide number, so a reload or a shared link opens the same slide.
(() => {
  const stage = document.getElementById('stage');
  const slides = [...stage.children];
  let current = 0;
  const show = (n) => {
    current = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((s, i) => s.classList.toggle('current', i === current));
    history.replaceState(null, '', '#' + (current + 1));
  };
  const fit = () => {
    const k = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `scale(${k}) translate(-50%, -50%)`;
  };
  addEventListener('resize', fit);
  addEventListener('keydown', (e) => {
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(e.key)) show(current + 1);
    else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)) show(current - 1);
    else if (e.key === 'Home') show(0);
    else if (e.key === 'End') show(slides.length - 1);
  });
  addEventListener('click', (e) => show(current + (e.clientX < innerWidth / 3 ? -1 : 1)));
  fit();
  show((parseInt(location.hash.slice(1), 10) || 1) - 1);
})();
