// Minimal calibration UI helpers; no styling changes
(function () {
  const api = {
    async getOffsets() {
      const res = await fetch('/api/offsets');
      if (!res.ok) throw new Error('Failed to fetch offsets');
      return (await res.json()).offsets || {};
    },
    async putOffsets(patch) {
      const res = await fetch('/api/offsets', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error('Failed to update offsets');
      return (await res.json()).offsets || {};
    },
    async zero(id) {
      const res = await fetch(`/api/zero/${encodeURIComponent(id)}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to zero ' + id);
      return await res.json();
    },
    async zeroAll() {
      const res = await fetch('/api/zero_all', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to zero all');
      return (await res.json()).offsets || {};
    },
    async resetAll() {
      const res = await fetch('/api/reset_offsets', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to reset all');
      return (await res.json()).offsets || {};
    },
  };

  function buildSection(container, sensors, title) {
    container.classList.add('calibration-block');

    const head = document.createElement('div');
    head.className = 'calibration-title';
    head.textContent = title;

    const controls = document.createElement('div');
    controls.className = 'calibration-controls';
    const zeroAllBtn = document.createElement('button');
    zeroAllBtn.textContent = 'Zero All';
    zeroAllBtn.addEventListener('click', async () => {
      try {
        await api.zeroAll();
        await refresh();
      } catch (e) { console.error(e); }
    });
    controls.appendChild(zeroAllBtn);

    const resetAllBtn = document.createElement('button');
    resetAllBtn.textContent = 'Reset All';
    resetAllBtn.style.marginLeft = '8px';
    resetAllBtn.addEventListener('click', async () => {
      try {
        await api.resetAll();
        await refresh();
      } catch (e) { console.error(e); }
    });
    controls.appendChild(resetAllBtn);

    const header = document.createElement('div');
    header.className = 'calibration-header';
    header.appendChild(head);
    header.appendChild(controls);
    container.appendChild(header);

    const list = document.createElement('div');
    list.className = 'calibration-rows';
    sensors.forEach(s => {
      const row = document.createElement('div');
      row.className = 'calibration-row';

      const swatch = document.createElement('span');
      swatch.className = 'calibration-swatch';
      if (s.color) swatch.style.backgroundColor = s.color;
      row.appendChild(swatch);

      const label = document.createElement('span');
      label.textContent = `${s.name} (${s.id})`;
      label.className = 'sensor-name';
      row.appendChild(label);

      const input = document.createElement('input');
      input.type = 'number';
      input.step = 'any';
      input.className = 'calibration-input';
      input.dataset.sensorId = s.id;
      row.appendChild(input);

      const updateBtn = document.createElement('button');
      updateBtn.textContent = 'Update';
      updateBtn.className = 'calibration-update';
      updateBtn.addEventListener('click', async () => {
        const val = parseFloat(input.value);
        if (!Number.isFinite(val)) return;
        try {
          await api.putOffsets({ [s.id]: val });
          await refresh();
        } catch (e) { console.error(e); }
      });
      row.appendChild(updateBtn);

      const zeroBtn = document.createElement('button');
      zeroBtn.textContent = 'Zero';
      zeroBtn.className = 'calibration-zero';
      zeroBtn.addEventListener('click', async () => {
        try {
          await api.zero(s.id);
          await refresh();
        } catch (e) { console.error(e); }
      });
      row.appendChild(zeroBtn);

      list.appendChild(row);
    });
    container.appendChild(list);

    async function refresh() {
      try {
        const offsets = await api.getOffsets();
        list.querySelectorAll('input[data-sensor-id]')
          .forEach(inp => { const id = inp.dataset.sensorId; inp.value = offsets[id] ?? 0; });
      } catch (e) { console.error(e); }
    }

    return { refresh };
  }

  function initPT() {
    const container = document.getElementById('calibration-pt');
    const cfg = (typeof Config !== 'undefined' ? Config : (window.Config || null));
    if (!container || !cfg || !Array.isArray(cfg.PRESSURE_TRANSDUCERS)) return;
    const { refresh } = buildSection(container, cfg.PRESSURE_TRANSDUCERS, 'Calibration — Pressure Transducers');
    refresh();
  }

  function initTCLC() {
    const container = document.getElementById('calibration-tc-lc');
    const cfg = (typeof Config !== 'undefined' ? Config : (window.Config || null));
    if (!container || !cfg) return;
    const sensors = [];
    (cfg.THERMOCOUPLES || []).forEach(s => sensors.push(s));
    (cfg.LOAD_CELLS || []).forEach(s => sensors.push(s));
    const { refresh } = buildSection(container, sensors, 'Calibration — Thermocouples & Load Cells');
    refresh();
  }

  window.Calibration = { initPT, initTCLC };
  // Auto-initialize when containers are present
  document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('calibration-pt') && window.Calibration && typeof window.Calibration.initPT === 'function') {
      window.Calibration.initPT();
    }
    if (document.getElementById('calibration-tc-lc') && window.Calibration && typeof window.Calibration.initTCLC === 'function') {
      window.Calibration.initTCLC();
    }
  });
})();
