/* =============================================================
   GradRegistry — main.js
   All frontend interactivity: nav, forms, modals, utilities
   ============================================================= */

'use strict';

/* ─────────────────────────────────────────────
   1. DOM READY HELPER
───────────────────────────────────────────── */
function ready(fn) {
  if (document.readyState !== 'loading') {
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

/* ─────────────────────────────────────────────
   2. MOBILE NAV TOGGLE
───────────────────────────────────────────── */
function initMobileNav() {
  const toggle = document.getElementById('nav-toggle');
  const menu   = document.getElementById('nav-menu');
  if (!toggle || !menu) return;

  toggle.addEventListener('click', function () {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    menu.classList.toggle('nav-open');
    // Swap hamburger ↔ ✕ icon
    toggle.innerHTML = expanded
      ? '<span class="hamburger">&#9776;</span>'
      : '<span class="hamburger">&#10005;</span>';
  });

  // Close menu when a nav link is clicked
  menu.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      menu.classList.remove('nav-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.innerHTML = '<span class="hamburger">&#9776;</span>';
    });
  });

  // Close on outside click
  document.addEventListener('click', function (e) {
    if (!toggle.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.remove('nav-open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.innerHTML = '<span class="hamburger">&#9776;</span>';
    }
  });
}

/* ─────────────────────────────────────────────
   3. FLASH MESSAGE AUTO-DISMISS
───────────────────────────────────────────── */
function initFlashMessages() {
  const flashes = document.querySelectorAll('.flash-message');
  flashes.forEach(function (flash) {
    // Auto-dismiss after 5 seconds
    const timer = setTimeout(function () {
      dismissFlash(flash);
    }, 5000);

    // Manual dismiss button
    const closeBtn = flash.querySelector('.flash-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () {
        clearTimeout(timer);
        dismissFlash(flash);
      });
    }
  });
}

function dismissFlash(flash) {
  flash.style.opacity = '0';
  flash.style.transform = 'translateX(110%)';
  setTimeout(function () {
    if (flash.parentNode) flash.parentNode.removeChild(flash);
  }, 350);
}

/* ─────────────────────────────────────────────
   4. PASSWORD STRENGTH INDICATOR
───────────────────────────────────────────── */
function initPasswordStrength() {
  const passwordInput = document.getElementById('password');
  const strengthBar   = document.getElementById('strength-bar');
  const strengthText  = document.getElementById('strength-text');

  if (!passwordInput || !strengthBar || !strengthText) return;

  passwordInput.addEventListener('input', function () {
    const val    = passwordInput.value;
    const score  = scorePassword(val);
    const labels = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const colors = ['', '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60'];

    strengthBar.style.width   = (score * 20) + '%';
    strengthBar.style.background = colors[score] || '#e0ddd8';
    strengthText.textContent  = score > 0 ? labels[score] : '';
    strengthText.style.color  = colors[score] || '';
  });
}

function scorePassword(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 5);
}

/* ─────────────────────────────────────────────
   5. TOGGLE PASSWORD VISIBILITY
───────────────────────────────────────────── */
function togglePassword(inputId, btnEl) {
  const input = document.getElementById(inputId);
  if (!input) return;

  if (input.type === 'password') {
    input.type = 'text';
    if (btnEl) btnEl.textContent = 'Hide';
  } else {
    input.type = 'password';
    if (btnEl) btnEl.textContent = 'Show';
  }
}

// Expose globally so onclick= attributes in templates work
window.togglePassword = togglePassword;

/* ─────────────────────────────────────────────
   6. COPY SHARE LINK
───────────────────────────────────────────── */
function copyShareLink(url) {
  if (!url) {
    // Try to grab from a data attribute on the button itself
    const btn = document.getElementById('copy-share-btn');
    url = btn ? btn.dataset.url : window.location.href;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(function () {
      showCopyFeedback();
    }).catch(function () {
      fallbackCopy(url);
    });
  } else {
    fallbackCopy(url);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity  = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    showCopyFeedback();
  } catch (e) {
    alert('Could not copy automatically. Please copy this link manually:\n' + text);
  }
  document.body.removeChild(ta);
}

function showCopyFeedback() {
  const btn = document.getElementById('copy-share-btn');
  if (!btn) return;
  const original = btn.textContent;
  btn.textContent = '✓ Copied!';
  btn.classList.add('copied');
  setTimeout(function () {
    btn.textContent = original;
    btn.classList.remove('copied');
  }, 2000);
}

// Expose globally
window.copyShareLink = copyShareLink;

/* ─────────────────────────────────────────────
   7. PUBLIC PROFILE — REGISTRY FILTER TABS
───────────────────────────────────────────── */
function initRegistryFilter() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const items      = document.querySelectorAll('.registry-card');

  if (!filterBtns.length || !items.length) return;

  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      // Toggle active state
      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');

      const filter = btn.dataset.filter;

      items.forEach(function (card) {
        if (filter === 'all') {
          card.style.display = '';
        } else if (filter === 'available') {
          card.style.display = card.dataset.purchased === 'true' ? 'none' : '';
        } else if (filter === 'claimed') {
          card.style.display = card.dataset.purchased === 'true' ? '' : 'none';
        } else {
          // Category filter
          card.style.display = card.dataset.category === filter ? '' : 'none';
        }
      });

      // Show empty state if nothing visible
      const grid       = document.getElementById('registry-grid');
      const emptyState = document.getElementById('registry-empty');
      if (grid && emptyState) {
        const visible = grid.querySelectorAll('.registry-card[style=""],.registry-card:not([style])');
        const anyVisible = Array.from(items).some(function (c) {
          return c.style.display !== 'none';
        });
        emptyState.style.display = anyVisible ? 'none' : '';
      }
    });
  });
}

/* ─────────────────────────────────────────────
   8. MARK AS PURCHASED MODAL
───────────────────────────────────────────── */
function initPurchaseModal() {
  const modal     = document.getElementById('purchase-modal');
  const closeBtn  = document.getElementById('modal-close');
  const cancelBtn = document.getElementById('modal-cancel');
  const form      = document.getElementById('purchase-form');

  if (!modal) return;

  // Open modal when "Mark as Purchased" is clicked
  document.querySelectorAll('.mark-purchased-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const itemId   = btn.dataset.itemId;
      const itemName = btn.dataset.itemName;

      // Set form action
      if (form) {
        const actionBase = form.dataset.actionBase || '/item/';
        form.action = actionBase + itemId + '/purchase';
      }

      // Update modal copy
      const nameEl = document.getElementById('modal-item-name');
      if (nameEl) nameEl.textContent = '"' + itemName + '"';

      openModal(modal);
    });
  });

  // Close handlers
  if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });
  if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });

  // Close on backdrop click
  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal(modal);
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.classList.contains('modal-open')) {
      closeModal(modal);
    }
  });
}

function openModal(modal) {
  modal.classList.add('modal-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  // Focus first focusable element
  const focusable = modal.querySelector('button, input, textarea, [tabindex]');
  if (focusable) setTimeout(function () { focusable.focus(); }, 50);
}

function closeModal(modal) {
  modal.classList.remove('modal-open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

/* ─────────────────────────────────────────────
   9. IMAGE URL PREVIEW
───────────────────────────────────────────── */
function initImagePreview() {
  const input   = document.getElementById('image_url');
  const preview = document.getElementById('image-preview');

  if (!input || !preview) return;

  function updatePreview() {
    const url = input.value.trim();
    if (url) {
      preview.src = url;
      preview.style.display = 'block';
      preview.onerror = function () {
        preview.style.display = 'none';
      };
    } else {
      preview.style.display = 'none';
    }
  }

  input.addEventListener('input', debounce(updatePreview, 600));
  // Show on page load if value already set (edit mode)
  updatePreview();
}

/* ─────────────────────────────────────────────
   10. PHOTO URL PREVIEW (profile edit)
───────────────────────────────────────────── */
function initPhotoPreview() {
  const input   = document.getElementById('photo_url');
  const preview = document.getElementById('photo-preview');

  if (!input || !preview) return;

  function updatePreview() {
    const url = input.value.trim();
    if (url) {
      preview.src = url;
      preview.style.display = 'block';
      preview.onerror = function () {
        preview.style.display = 'none';
      };
    } else {
      preview.style.display = 'none';
    }
  }

  input.addEventListener('input', debounce(updatePreview, 600));
  updatePreview();
}

/* ─────────────────────────────────────────────
   11. CHARACTER COUNTER
───────────────────────────────────────────── */
function initCharCounters() {
  document.querySelectorAll('[data-max-chars]').forEach(function (el) {
    const max     = parseInt(el.dataset.maxChars, 10);
    const countEl = document.getElementById(el.id + '-count');
    if (!countEl) return;

    function update() {
      const remaining = max - el.value.length;
      countEl.textContent = remaining + ' characters remaining';
      countEl.classList.toggle('char-warning', remaining < 50);
      countEl.classList.toggle('char-danger',  remaining < 10);
    }

    el.addEventListener('input', update);
    update();
  });
}

/* ─────────────────────────────────────────────
   12. PUBLIC PROFILE — STICKY NAV HIGHLIGHT
───────────────────────────────────────────── */
function initStickyProfileNav() {
  const navLinks = document.querySelectorAll('.profile-nav-link');
  const sections = document.querySelectorAll('.profile-section[id]');

  if (!navLinks.length || !sections.length) return;

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        navLinks.forEach(function (link) {
          link.classList.toggle(
            'active',
            link.getAttribute('href') === '#' + entry.target.id
          );
        });
      }
    });
  }, { rootMargin: '-20% 0px -70% 0px' });

  sections.forEach(function (sec) { observer.observe(sec); });
}

/* ─────────────────────────────────────────────
   13. SCROLL TO ANCHOR (smooth, offset for sticky nav)
───────────────────────────────────────────── */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const id = anchor.getAttribute('href').slice(1);
      const target = id ? document.getElementById(id) : null;
      if (!target) return;
      e.preventDefault();

      const offset = 80; // height of sticky nav
      const top    = target.getBoundingClientRect().top + window.pageYOffset - offset;
      window.scrollTo({ top: top, behavior: 'smooth' });

      // Update URL hash without jumping
      if (history.pushState) {
        history.pushState(null, null, '#' + id);
      }
    });
  });
}

/* ─────────────────────────────────────────────
   14. CONFIRM DANGEROUS ACTIONS
───────────────────────────────────────────── */
function initDangerConfirm() {
  // Account delete — type email to confirm
  const deleteForm    = document.getElementById('delete-account-form');
  const confirmInput  = document.getElementById('confirm-email-input');
  const deleteBtn     = document.getElementById('delete-account-btn');
  const expectedEmail = deleteBtn ? deleteBtn.dataset.email : null;

  if (deleteForm && confirmInput && deleteBtn && expectedEmail) {
    confirmInput.addEventListener('input', function () {
      deleteBtn.disabled = confirmInput.value.trim() !== expectedEmail;
    });
    deleteBtn.disabled = true; // start disabled

    deleteForm.addEventListener('submit', function (e) {
      if (confirmInput.value.trim() !== expectedEmail) {
        e.preventDefault();
        alert('Please type your email address exactly to confirm deletion.');
      }
    });
  }

  // Generic data-confirm buttons (e.g., delete registry item)
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      const msg = el.dataset.confirm || 'Are you sure?';
      if (!window.confirm(msg)) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    });
  });
}

/* ─────────────────────────────────────────────
   15. SEARCH FORM — LIVE FEEDBACK
───────────────────────────────────────────── */
function initSearchForm() {
  const form  = document.getElementById('search-form');
  const input = document.getElementById('search-input');
  if (!form || !input) return;

  // Trim whitespace before submit
  form.addEventListener('submit', function () {
    input.value = input.value.trim();
  });
}

/* ─────────────────────────────────────────────
   16. DASHBOARD — CHECKLIST PROGRESS
───────────────────────────────────────────── */
function initChecklistProgress() {
  const checks  = document.querySelectorAll('.checklist-item');
  const bar     = document.getElementById('checklist-progress-bar');
  const label   = document.getElementById('checklist-progress-label');
  if (!checks.length || !bar) return;

  const done  = Array.from(checks).filter(function (c) {
    return c.classList.contains('complete');
  }).length;
  const total = checks.length;
  const pct   = Math.round((done / total) * 100);

  bar.style.width = pct + '%';
  if (label) label.textContent = done + ' of ' + total + ' steps complete';
}

/* ─────────────────────────────────────────────
   17. SCROLL-REVEAL ANIMATION (lightweight)
───────────────────────────────────────────── */
function initScrollReveal() {
  const revealEls = document.querySelectorAll('.reveal');
  if (!revealEls.length) return;

  // Reduced-motion check
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) {
    revealEls.forEach(function (el) { el.classList.add('revealed'); });
    return;
  }

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  revealEls.forEach(function (el) { observer.observe(el); });
}

/* ─────────────────────────────────────────────
   18. TOOLTIP INITIALIZER
───────────────────────────────────────────── */
function initTooltips() {
  document.querySelectorAll('[data-tooltip]').forEach(function (el) {
    let tip;

    el.addEventListener('mouseenter', function () {
      tip = document.createElement('div');
      tip.className   = 'tooltip-popup';
      tip.textContent = el.dataset.tooltip;
      document.body.appendChild(tip);

      const rect = el.getBoundingClientRect();
      tip.style.left = (rect.left + rect.width / 2 - tip.offsetWidth / 2) + 'px';
      tip.style.top  = (rect.top - tip.offsetHeight - 8 + window.scrollY) + 'px';
    });

    el.addEventListener('mouseleave', function () {
      if (tip && tip.parentNode) tip.parentNode.removeChild(tip);
    });
  });
}

/* ─────────────────────────────────────────────
   19. PRINT PARTY DETAILS
───────────────────────────────────────────── */
function printPartyDetails() {
  window.print();
}
window.printPartyDetails = printPartyDetails;

/* ─────────────────────────────────────────────
   20. UTILITY: DEBOUNCE
───────────────────────────────────────────── */
function debounce(fn, delay) {
  let timer;
  return function () {
    const ctx  = this;
    const args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
  };
}

/* ─────────────────────────────────────────────
   21. UTILITY: FORMAT CURRENCY
───────────────────────────────────────────── */
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style:    'currency',
    currency: 'USD'
  }).format(amount);
}

/* ─────────────────────────────────────────────
   22. REGISTRY ITEM PRICE DISPLAY
───────────────────────────────────────────── */
function initPriceDisplay() {
  document.querySelectorAll('.item-price[data-amount]').forEach(function (el) {
    const raw = parseFloat(el.dataset.amount);
    if (!isNaN(raw)) {
      el.textContent = formatCurrency(raw);
    }
  });
}

/* ─────────────────────────────────────────────
   23. EXTERNAL LINK SAFETY BANNER
   Shows a brief "You're leaving GradRegistry" tooltip
   for all outbound links with target="_blank"
───────────────────────────────────────────── */
function initExternalLinkWarning() {
  document.querySelectorAll('a[target="_blank"]').forEach(function (link) {
    link.setAttribute('rel', 'noopener noreferrer');
    // Only add data-tooltip if not already set
    if (!link.dataset.tooltip && link.hostname && link.hostname !== window.location.hostname) {
      link.dataset.tooltip = 'Opens in a new tab';
    }
  });
}

/* ─────────────────────────────────────────────
   24. FORM SUBMIT LOADING STATE
───────────────────────────────────────────── */
function initFormLoadingState() {
  document.querySelectorAll('form[data-loading]').forEach(function (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) {
        const loadingText = form.dataset.loading || 'Saving…';
        btn.disabled     = true;
        btn.dataset.orig  = btn.textContent;
        btn.textContent  = loadingText;
      }
    });
  });
}

/* ─────────────────────────────────────────────
   25. BACK-TO-TOP BUTTON
───────────────────────────────────────────── */
function initBackToTop() {
  const btn = document.getElementById('back-to-top');
  if (!btn) return;

  window.addEventListener('scroll', debounce(function () {
    btn.classList.toggle('visible', window.scrollY > 400);
  }, 100));

  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

/* ─────────────────────────────────────────────
   INIT — Run everything on DOM ready
───────────────────────────────────────────── */
ready(function () {
  initMobileNav();
  initFlashMessages();
  initPasswordStrength();
  initImagePreview();
  initPhotoPreview();
  initCharCounters();
  initStickyProfileNav();
  initSmoothScroll();
  initDangerConfirm();
  initSearchForm();
  initChecklistProgress();
  initScrollReveal();
  initTooltips();
  initPriceDisplay();
  initExternalLinkWarning();
  initFormLoadingState();
  initBackToTop();
  initRegistryFilter();
  initPurchaseModal();
});
