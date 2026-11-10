(function () {
  'use strict';
  var ctx = window.WEBTOON || {};
  var episodes = ctx.episodes || [];
  var seriesId = ctx.seriesId || '';
  var seriesTitle = ctx.seriesTitle || '';
  var keys = {
    progress: 'webtoon-progress-v1-' + (seriesId || 'site'),
    preferences: 'webtoon-preferences-v1'
  };

  function readStored(key) {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (_) { return null; }
  }
  function writeStored(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (_) { return false; }
  }
  function findEpisode(number) {
    return episodes.find(function (ep) { return ep.number === Number(number); });
  }
  function validProgress(value) {
    return value && findEpisode(value.episode) && Number.isFinite(value.fraction) && value.fraction >= 0 && value.fraction <= 1;
  }

  var saved = seriesId ? readStored(keys.progress) : null;
  if (validProgress(saved)) {
    document.querySelectorAll('[data-resume-link]').forEach(function (link) {
      var episode = findEpisode(saved.episode);
      if (!episode) return;
      link.href = episode.url + '?resume=1';
      var label = link.querySelector('[data-button-label]');
      if (label) {
        label.textContent = (episode.kind === 'concept' ? episode.shortLabel + ' 이어보기' : saved.episode + '화 이어읽기');
      }
    });
    document.querySelectorAll('[data-read-status]').forEach(function (node) {
      if (Number(node.dataset.readStatus) === saved.episode) {
        node.hidden = false;
        node.textContent = '읽던 곳 · ' + Math.round(saved.fraction * 100) + '%';
      }
    });
  }

  if (!document.body.classList.contains('reader')) return;

  var body = document.body;
  var settings = readStored(keys.preferences) || { backdrop: 'dark', width: 820 };
  function applySettings() {
    body.dataset.backdrop = settings.backdrop === 'light' ? 'light' : 'dark';
    body.style.setProperty('--reader-width', (settings.width === 1024 ? 1024 : 820) + 'px');
    document.querySelectorAll('[name="backdrop"]').forEach(function (input) {
      input.checked = input.value === body.dataset.backdrop;
    });
    document.querySelectorAll('[name="width"]').forEach(function (input) {
      input.checked = Number(input.value) === (settings.width === 1024 ? 1024 : 820);
    });
  }
  applySettings();

  var sections = Array.from(document.querySelectorAll('.chapter'));
  var active = sections[0];
  var fraction = 0;
  var scheduled = false;
  var scrollIntent = false;
  var restored = false;
  var saveTimer;
  var toastTimer;
  var currentLabel = document.querySelector('[data-current-title]');
  var dockEpisode = document.querySelector('[data-dock-episode]');
  var dockProgress = document.querySelector('[data-dock-progress]');
  var progressBar = document.querySelector('.reader-progress-fill');

  function refreshProgress() {
    scheduled = false;
    var marker = window.scrollY + Math.min(window.innerHeight * 0.28, 180);
    active = sections[0];
    sections.forEach(function (section) {
      if (section.offsetTop <= marker) active = section;
    });
    if (!active) return;
    var art = active.querySelector('.episode-art');
    var artTop = art.getBoundingClientRect().top + window.scrollY;
    fraction = Math.max(0, Math.min(1, (window.scrollY - artTop + 65) / Math.max(1, art.offsetHeight - window.innerHeight + 65)));
    var number = Number(active.dataset.episode);
    var episode = findEpisode(number) || {};
    if (currentLabel) currentLabel.textContent = episode.displayTitle || (number + '화');
    if (dockEpisode) dockEpisode.textContent = episode.shortLabel || (number + '화');
    if (dockProgress) dockProgress.textContent = Math.round(fraction * 100) + '%';
    if (progressBar) progressBar.style.width = (fraction * 100) + '%';
    var prev = document.querySelector('[data-prev]');
    var next = document.querySelector('[data-next]');
    if (prev) prev.disabled = !episodes.length || number === episodes[0].number;
    if (next) next.disabled = !episodes.length || number === episodes[episodes.length - 1].number;
    document.querySelectorAll('[data-episode-link]').forEach(function (link) {
      link.setAttribute('aria-current', String(Number(link.dataset.episodeLink) === number));
    });
    if (episode.title) {
      document.title = (episode.displayTitle || (number + '화 ' + episode.title)) + (seriesTitle ? ' · ' + seriesTitle : '');
    }
    if (restored && scrollIntent) {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(saveProgress, 450);
    }
  }

  function saveProgress() {
    if (!active || !restored || !scrollIntent || !seriesId) return;
    writeStored(keys.progress, {
      episode: Number(active.dataset.episode),
      fraction: fraction,
      updatedAt: Date.now()
    });
  }

  function requestProgress() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(refreshProgress);
    }
  }

  function showToast(message) {
    var node = document.querySelector('.toast');
    if (!node) return;
    node.textContent = message;
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { node.hidden = true; }, 2200);
  }

  function goToEpisode(number) {
    var episode = findEpisode(number);
    if (!episode) return;
    var target = document.getElementById('ep-' + number);
    if (!target) {
      saveProgress();
      location.assign(episode.url);
      return;
    }
    document.querySelectorAll('dialog[open]').forEach(function (dialog) { dialog.close(); });
    history.replaceState(null, '', '#ep-' + number);
    scrollIntent = true;
    target.scrollIntoView({ behavior: 'auto', block: 'start' });
    requestProgress();
  }

  document.querySelectorAll('[data-dialog]').forEach(function (button) {
    button.addEventListener('click', function () {
      var dialog = document.getElementById(button.dataset.dialog);
      if (dialog) dialog.showModal();
    });
  });
  document.querySelectorAll('[data-close-dialog]').forEach(function (button) {
    button.addEventListener('click', function () {
      button.closest('dialog').close();
    });
  });
  document.querySelectorAll('dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) {
        var r = dialog.getBoundingClientRect();
        if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) {
          dialog.close();
        }
      }
    });
  });
  document.querySelectorAll('[data-episode-link]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      if (link.getAttribute('href') && !document.getElementById('ep-' + link.dataset.episodeLink)) return;
      event.preventDefault();
      goToEpisode(Number(link.dataset.episodeLink));
    });
  });

  var prevBtn = document.querySelector('[data-prev]');
  var nextBtn = document.querySelector('[data-next]');
  if (prevBtn) {
    prevBtn.addEventListener('click', function () {
      var i = episodes.findIndex(function (ep) { return ep.number === Number(active.dataset.episode); });
      if (i > 0) goToEpisode(episodes[i - 1].number);
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', function () {
      var i = episodes.findIndex(function (ep) { return ep.number === Number(active.dataset.episode); });
      if (i < episodes.length - 1) goToEpisode(episodes[i + 1].number);
    });
  }
  var topBtn = document.querySelector('[data-top]');
  if (topBtn) {
    topBtn.addEventListener('click', function () {
      goToEpisode(Number(active.dataset.episode));
    });
  }
  var bookmarkBtn = document.querySelector('[data-bookmark]');
  if (bookmarkBtn) {
    bookmarkBtn.addEventListener('click', function () {
      scrollIntent = true;
      var ok = writeStored(keys.progress, {
        episode: Number(active.dataset.episode),
        fraction: fraction,
        updatedAt: Date.now()
      });
      showToast(ok ? '읽던 위치를 저장했어요.' : '이 브라우저에서는 위치를 저장할 수 없어요.');
    });
  }
  var focusButton = document.querySelector('[data-focus]');
  if (focusButton) {
    focusButton.addEventListener('click', function () {
      var focused = body.classList.toggle('is-focused');
      focusButton.setAttribute('aria-pressed', String(focused));
      focusButton.setAttribute('aria-label', focused ? '메뉴 표시' : '집중해서 읽기');
    });
  }
  document.querySelectorAll('[name="backdrop"],[name="width"]').forEach(function (input) {
    input.addEventListener('change', function () {
      var number = active ? Number(active.dataset.episode) : (episodes[0] && episodes[0].number);
      var oldFraction = fraction;
      if (input.name === 'width') settings.width = Number(input.value);
      else settings.backdrop = input.value;
      applySettings();
      writeStored(keys.preferences, settings);
      if (input.name === 'width' && number) restorePosition(number, oldFraction);
    });
  });

  function restorePosition(number, position) {
    var section = document.getElementById('ep-' + number);
    if (!section) return;
    var art = section.querySelector('.episode-art');
    var top = art.getBoundingClientRect().top + window.scrollY;
    var h = parseFloat(getComputedStyle(body).getPropertyValue('--header-h')) || 66;
    var range = Math.max(1, art.offsetHeight - window.innerHeight + 65);
    window.scrollTo({ top: Math.max(0, top - h + position * range), behavior: 'auto' });
  }

  window.addEventListener('wheel', function () { scrollIntent = true; }, { passive: true });
  window.addEventListener('touchstart', function () { scrollIntent = true; }, { passive: true });
  window.addEventListener('keydown', function (event) {
    if (['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', ' ', 'Home', 'End'].includes(event.key)) scrollIntent = true;
  });
  window.addEventListener('scroll', requestProgress, { passive: true });
  window.addEventListener('resize', requestProgress, { passive: true });
  window.addEventListener('pagehide', saveProgress);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') saveProgress();
  });
  window.addEventListener('hashchange', function () {
    var match = location.hash.match(/^#ep-(\d+)$/);
    if (match) goToEpisode(Number(match[1]));
  });
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      var resume = new URLSearchParams(location.search).has('resume');
      var currentNumber = active ? Number(active.dataset.episode) : 0;
      if (resume && validProgress(saved) && saved.episode === currentNumber) {
        restorePosition(currentNumber, saved.fraction);
        history.replaceState(null, '', location.pathname + '#ep-' + currentNumber);
      } else if (currentNumber) {
        restorePosition(currentNumber, 0);
      }
      restored = true;
      refreshProgress();
    });
  });
})();
