// Arrastrar y soltar tarjetas (mejora progresiva: sin JS siguen funcionando los botones).
// Al soltar se mueve la tarjeta en la página y se avisa al servidor con fetch.
'use strict';

(function () {
  const listas = document.querySelectorAll('.lista-tarjetas');
  if (!listas.length) return;

  const token = document.querySelector('meta[name="csrf"]')?.content ?? '';
  let arrastrada = null;

  // Tarjeta de la lista que queda justo debajo del puntero (o null si va al final)
  function tarjetaDebajo(lista, y) {
    const otras = [...lista.querySelectorAll('.tarjeta:not(.arrastrando)')];
    return otras.find((t) => {
      const caja = t.getBoundingClientRect();
      return y < caja.top + caja.height / 2;
    }) ?? null;
  }

  // Envía el movimiento; si falla, recargamos para mostrar el estado real
  async function guardar(tarjeta) {
    const lista = tarjeta.parentElement;
    const datos = new FormData();
    datos.append('_token', token);
    datos.append('ajax', '1');
    datos.append('columna_id', lista.dataset.columna);
    datos.append('posicion', [...lista.children].indexOf(tarjeta));
    try {
      const resp = await fetch(`/tarjetas/${tarjeta.dataset.id}/mover`, { method: 'POST', body: datos });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    } catch (err) {
      console.error('No se pudo mover la tarjeta:', err);
    }
    // Recargar actualiza contadores y botones ← ↑ ↓ → habilitados
    location.reload();
  }

  document.querySelectorAll('.tarjeta[draggable]').forEach((tarjeta) => {
    tarjeta.addEventListener('dragstart', (ev) => {
      arrastrada = tarjeta;
      tarjeta.classList.add('arrastrando');
      ev.dataTransfer.effectAllowed = 'move';
      ev.dataTransfer.setData('text/plain', tarjeta.dataset.id);
    });
    tarjeta.addEventListener('dragend', () => {
      tarjeta.classList.remove('arrastrando');
      listas.forEach((l) => l.classList.remove('destino'));
    });
  });

  listas.forEach((lista) => {
    lista.addEventListener('dragover', (ev) => {
      if (!arrastrada) return;
      ev.preventDefault(); // necesario para permitir soltar
      lista.classList.add('destino');
      const siguiente = tarjetaDebajo(lista, ev.clientY);
      if (siguiente) lista.insertBefore(arrastrada, siguiente);
      else lista.appendChild(arrastrada);
    });
    lista.addEventListener('dragleave', () => lista.classList.remove('destino'));
    lista.addEventListener('drop', (ev) => {
      ev.preventDefault();
      if (!arrastrada) return;
      const tarjeta = arrastrada;
      arrastrada = null;
      guardar(tarjeta);
    });
  });
})();
