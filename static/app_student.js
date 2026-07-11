(() => {
  const runSpeechBtn = document.getElementById('runSpeechBtn');
  const qEl = document.getElementById('q');
  const sortEl = document.getElementById('sort');
  const refreshBtn = document.getElementById('refreshBtn');

  function go() {
    const q = encodeURIComponent((qEl?.value || '').trim());
    const sort = encodeURIComponent(sortEl?.value || 'new');
    location.href = `/student?q=${q}&sort=${sort}`;
  }

  refreshBtn?.addEventListener('click', go);
  qEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') go();
  });
  sortEl?.addEventListener('change', go);

  document.addEventListener(
    'play',
    (e) => {
      document.querySelectorAll('audio').forEach((a) => {
        if (a !== e.target) a.pause();
      });
    },
    true
  );

  runSpeechBtn?.addEventListener('click', () => {
  window.open('/run_speech', '_blank', 'noopener,noreferrer');
});



  let modal, modalTitle, modalContent;

  function cacheEls() {
    modal = document.getElementById('textModal');
    modalTitle = document.getElementById('modalTitle');
    modalContent = document.getElementById('modalContent');
  }

  function showModal() {
    if (!modal) cacheEls();
    if (!modal) return;

    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!modal) cacheEls();
    if (!modal) return;

    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  async function openText(kind, fileName) {
    if (!modal) cacheEls();
    if (!modalTitle || !modalContent) return;

    modalTitle.textContent =
      kind === 'summery' ? ` ${fileName}` : ` ${fileName}`;

    modalContent.textContent = 'در حال بارگذاری...';
    showModal();

    try {
      const url = `/api/text/${encodeURIComponent(kind)}?file=${encodeURIComponent(
        fileName
      )}`;

      const res = await fetch(url, { headers: { Accept: 'application/json' } });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.ok) {
        modalContent.textContent = data?.error
          ? ` ${data.error}`
          : 'خطا در دریافت متن';
        return;
      }

      modalContent.textContent = data.text || '';
    } catch (e) {
      modalContent.textContent = ' ' + (e?.message || String(e));
    }
  }


  window.openText = openText;
  window.closeModal = closeModal;


  document.addEventListener('DOMContentLoaded', () => {
    cacheEls();


    const overlay = document.querySelector('#textModal .modal-overlay');
    if (overlay) overlay.addEventListener('click', closeModal);


    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
        closeModal();
      }
    });
  });
})();
