// JavaScript global do projeto (puro, sem frameworks). Carregado com defer pelo base.html.

/**
 * Lê um cookie pelo nome (ex.: o csrftoken do Django).
 * @param {string} nome
 * @returns {string|null}
 */
function lerCookie(nome) {
  const item = document.cookie.split('; ').find((c) => c.startsWith(nome + '='));
  return item ? decodeURIComponent(item.split('=')[1]) : null;
}

/**
 * fetch com o token CSRF do Django já incluído, para POST/PUT/PATCH/DELETE.
 * Uso: const resp = await requisicao('/clientes/novo/', { method: 'POST', body: new FormData(form) });
 */
function requisicao(url, opcoes = {}) {
  const headers = new Headers(opcoes.headers || {});
  const csrf = lerCookie('csrftoken');
  if (csrf) headers.set('X-CSRFToken', csrf);
  return fetch(url, { credentials: 'same-origin', ...opcoes, headers });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-ano-atual]').forEach((el) => {
    el.textContent = new Date().getFullYear();
  });
});
