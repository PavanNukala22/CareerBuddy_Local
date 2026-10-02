/* Behaviour for the one navbar (templates/includes/site_nav.html).
 *
 * It lives in a file rather than inline so the landing page and every
 * base.html page run exactly the same code. The guard below makes a second
 * include a no-op: the landing page used to carry its own copy of the mega-menu
 * and burger handlers, and binding both would toggle each menu twice per click.
 */
(function () {
  if (window.__cbSiteNavReady) { return; }
  window.__cbSiteNavReady = true;

  var ready = function (fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  };

  ready(function () {
    var nav = document.getElementById('cbMainNav');
    var burger = document.getElementById('cbBurger');
    var mobileMenu = document.getElementById('cbMobileMenu');
    var acct = document.getElementById('cbAcct');
    var acctBtn = document.getElementById('cbAcctBtn');

    function closeMegas() {
      if (!nav) { return; }
      nav.querySelectorAll(':scope > .nav-item.open').forEach(function (item) {
        item.classList.remove('open');
        var trigger = item.querySelector('button.nav-link');
        if (trigger) { trigger.setAttribute('aria-expanded', 'false'); }
      });
    }

    function closeAccount() {
      if (!acct) { return; }
      acct.classList.remove('open');
      if (acctBtn) { acctBtn.setAttribute('aria-expanded', 'false'); }
    }

    // ---- desktop mega menus -------------------------------------------
    if (nav) {
      nav.querySelectorAll(':scope > .nav-item').forEach(function (item) {
        var trigger = item.querySelector('button.nav-link');
        if (!trigger) { return; }
        trigger.addEventListener('click', function (e) {
          e.stopPropagation();
          var wasOpen = item.classList.contains('open');
          closeMegas();
          closeAccount();
          if (!wasOpen) {
            item.classList.add('open');
            trigger.setAttribute('aria-expanded', 'true');
          }
        });
      });
    }

    // ---- account dropdown ---------------------------------------------
    if (acct && acctBtn) {
      acctBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        var wasOpen = acct.classList.contains('open');
        closeMegas();
        closeAccount();
        if (!wasOpen) {
          acct.classList.add('open');
          acctBtn.setAttribute('aria-expanded', 'true');
          // Hand focus to the first entry so the menu is usable from the
          // keyboard alone, which is also what a screen reader expects after
          // a menu button reports aria-expanded="true".
          var first = acct.querySelector('.acct-item');
          if (first) { first.focus(); }
        }
      });

      // Choosing an entry closes the menu. Logout is a form submit rather than
      // a link, so this covers buttons as well as anchors.
      acct.querySelectorAll('.acct-item').forEach(function (item) {
        item.addEventListener('click', function () { closeAccount(); });
      });

      // Arrow keys walk the entries; Escape returns focus to the button.
      acct.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') { return; }
        var items = Array.prototype.slice.call(acct.querySelectorAll('.acct-item'));
        if (!items.length) { return; }
        e.preventDefault();
        var at = items.indexOf(document.activeElement);
        var next = e.key === 'ArrowDown' ? at + 1 : at - 1;
        if (next < 0) { next = items.length - 1; }
        if (next >= items.length) { next = 0; }
        items[next].focus();
      });
    }

    // ---- dismissal: outside click + Escape ------------------------------
    document.addEventListener('click', function () {
      closeMegas();
      closeAccount();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') { return; }
      var accountWasOpen = acct && acct.classList.contains('open');
      closeMegas();
      closeAccount();
      if (accountWasOpen && acctBtn) { acctBtn.focus(); }
      if (mobileMenu && mobileMenu.classList.contains('open')) {
        mobileMenu.classList.remove('open');
        if (burger) { burger.setAttribute('aria-expanded', 'false'); }
      }
    });

    // The dropdowns sit inside the header, so a click on one must not count as
    // a click "outside" and immediately close it again.
    document.querySelectorAll('.cb-nav .mega, .cb-nav .acct-menu').forEach(function (panel) {
      panel.addEventListener('click', function (e) { e.stopPropagation(); });
    });

    // ---- mobile menu ----------------------------------------------------
    if (burger && mobileMenu) {
      burger.addEventListener('click', function (e) {
        e.stopPropagation();
        var open = mobileMenu.classList.toggle('open');
        burger.setAttribute('aria-expanded', String(open));
      });
      mobileMenu.addEventListener('click', function (e) { e.stopPropagation(); });

      mobileMenu.querySelectorAll('.mm-item > .mm-trigger').forEach(function (trigger) {
        trigger.addEventListener('click', function (e) {
          if (e.target.closest('a')) { return; }   // plain link row: let it navigate
          trigger.closest('.mm-item').classList.toggle('open');
        });
      });

      // Close the overlay once an entry is chosen. Entries that leave the page
      // unload it anyway; the ones that jump to a section of this page would
      // otherwise scroll underneath a menu that is still covering the screen.
      mobileMenu.querySelectorAll('a[href]').forEach(function (link) {
        link.addEventListener('click', function () {
          mobileMenu.classList.remove('open');
          burger.setAttribute('aria-expanded', 'false');
        });
      });
    }
  });
})();
