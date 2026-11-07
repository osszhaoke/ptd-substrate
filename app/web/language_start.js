/* First launch and fixed home labels for the partner edition. Preference storage belongs to PTDS_LANGUAGE. */
(function (root) {
  'use strict';
  const doc = root.document;

  function systemLanguage() {
    const nav = root.navigator || {};
    const tags = [...(nav.languages || []), nav.language];
    for (const tag of tags) {
      const family = String(tag || '').toLowerCase().split(/[-_]/)[0];
      if (family === 'zh' || family === 'en') return family;
    }
    return 'en';
  }

  function show(onChoose) {
    const dialog = doc.createElement('dialog');
    dialog.id = 'first-language';
    dialog.setAttribute('aria-labelledby', 'first-language-title');
    function element(parent, tag, attrs, id, lang) {
      const node = doc.createElement(tag);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      if (id) node.textContent = message(id, lang);
      parent.appendChild(node);
      return node;
    }
    const title = element(dialog, 'h1', {id: 'first-language-title'});
    element(title, 'span', {lang: 'en'}, 'first_language_title', 'en');
    element(title, 'span', {lang: 'zh-CN'}, 'first_language_title', 'zh');
    const choices = element(dialog, 'div', {class: 'first-language-options', dir: 'ltr'});
    for (const lang of ['en', 'zh']) {
      element(choices, 'button', {type: 'button', lang: lang === 'en' ? 'en' : 'zh-CN', 'data-pick': lang}, 'first_language_' + lang, lang);
    }
    const system = element(dialog, 'button', {type: 'button', class: 'first-language-system', 'data-pick': 'system', autofocus: ''});
    element(system, 'span', {lang: 'en'}, 'first_language_system', 'en');
    system.appendChild(doc.createTextNode(' / '));
    element(system, 'span', {lang: 'zh-CN'}, 'first_language_system', 'zh');
    function finish(mode) {
      dialog.close();
      dialog.remove();
      onChoose(mode);
    }
    dialog.addEventListener('click', function (event) {
      const button = event.target.closest('button[data-pick]');
      if (button) finish(button.dataset.pick);
    });
    dialog.addEventListener('cancel', function (event) {
      event.preventDefault();
      finish('system');
    });
    doc.body.appendChild(dialog);
    dialog.showModal();
  }

  // These selectors belong to the partner launch renderer. Card names and custom titles are user input.
  function message(id, language) {
    return root.PTDS_LANGUAGE_RESOURCES.messages[id][language];
  }
  function home(language, label) {
    const launch = doc.querySelector('.launch');
    if (!launch) return;
    label(launch.querySelector('.subname'), null, ['brand']);
    launch.querySelectorAll('.modules > span').forEach(el => label(el, null, ['track_eyebrow', 'torch_eyebrow', 'cluster_eyebrow']));
    launch.querySelectorAll('button[data-launch]').forEach(el => label(el, null, ['launch_open']));
    const homeData = root.PTDS_LIVE && root.PTDS_LIVE.home && root.PTDS_LIVE.home();
    if (homeData && homeData.edited_title === false) label(doc.getElementById('home-title'), null, ['launch_motto']);
    label(doc.getElementById('disc'), null, ['launch_disclaimer']);
    const group = launch.querySelector('.icards');
    if (group) group.setAttribute('aria-label', message('launch_group', language));
    const gear = doc.getElementById('home-tgear');
    if (gear) {
      const title = message('launch_edit_title', language);
      gear.title = title;
      gear.setAttribute('aria-label', title);
    }
  }
  root.PTDS_FIRST_LANGUAGE = Object.freeze({systemLanguage, show, home});
})(window);
