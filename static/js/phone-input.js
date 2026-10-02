// Country-code phone input widget — pairs with templates/includes/phone_input.html.
// Keeps a hidden Django field in sync as "+<dial code><digits>" so the server
// (users/forms.py: validate_international_mobile, using the `phonenumbers`
// library) validates the number against the selected country.
(function () {
    function closeAllMenus(except) {
        document.querySelectorAll('.phone-country-select.open').forEach(function (el) {
            if (el !== except) {
                el.classList.remove('open');
                var btn = el.querySelector('.phone-country-btn');
                if (btn) btn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Fallback for the rare iso2 missing from COUNTRY_PHONE_LENGTHS (there
    // shouldn't be one — every COUNTRY_CODES entry has a matching entry —
    // but this keeps the widget working even if that dataset is edited later
    // without updating both in lockstep.
    var DEFAULT_LEN_RANGE = [4, 15];

    function lengthRangeFor(iso2) {
        var table = window.COUNTRY_PHONE_LENGTHS || {};
        return table[iso2] || DEFAULT_LEN_RANGE;
    }

    function syncHidden(widget) {
        var hidden = document.getElementById(widget.dataset.target);
        var numberInput = widget.querySelector('.phone-number-input');
        var dialEl = widget.querySelector('.phone-country-dial');
        if (!hidden || !numberInput || !dialEl) return;
        var digits = numberInput.value.replace(/\D/g, '');
        hidden.value = digits ? (dialEl.textContent + digits) : '';
    }

    function describeExpectedLength(range) {
        return range[0] === range[1]
            ? (range[0] + '-digit number')
            : (range[0] + '–' + range[1] + ' digit number');
    }

    // Applies the selected country's expected digit count: caps how much the
    // user can type, updates the placeholder hint, and re-checks whatever
    // digits are already there so switching country revalidates immediately.
    function applyLengthConstraints(widget, country) {
        var numberInput = widget.querySelector('.phone-number-input');
        var range = lengthRangeFor(country.iso2);
        numberInput.maxLength = range[1];
        numberInput.placeholder = describeExpectedLength(range) + (widget.dataset.placeholderSuffix || '');
        if (numberInput.value.replace(/\D/g, '').length > range[1]) {
            numberInput.value = numberInput.value.replace(/\D/g, '').slice(0, range[1]);
        }
        validateWidget(widget, { onlyIfDirty: true });
    }

    function setError(widget, message) {
        var numberInput = widget.querySelector('.phone-number-input');
        var errorEl = widget.querySelector('.phone-input-error');
        numberInput.classList.toggle('is-invalid', Boolean(message));
        if (errorEl) {
            errorEl.textContent = message || '';
            errorEl.style.display = message ? 'block' : 'none';
        }
    }

    // Live per-country digit-count check. `onlyIfDirty` skips showing an
    // error for a field the user hasn't touched yet (e.g. right after a
    // country switch on an still-empty field), but always re-validates
    // digits that are already present.
    function validateWidget(widget, opts) {
        opts = opts || {};
        var numberInput = widget.querySelector('.phone-number-input');
        var digits = numberInput.value.replace(/\D/g, '');
        var iso2 = widget.dataset.iso2;
        var country = (window.COUNTRY_CODES || []).find(function (c) { return c.iso2 === iso2; });
        var range = lengthRangeFor(iso2);

        if (!digits) {
            if (widget.dataset.required === '1') {
                if (opts.onlyIfDirty && !widget.dataset.touched) return false;
                setError(widget, 'This field is required.');
                return false;
            }
            setError(widget, '');
            return true;
        }
        if (digits.length < range[0] || digits.length > range[1]) {
            if (opts.onlyIfDirty && !widget.dataset.touched) return false;
            var countryName = country ? country.name : 'the selected country';
            setError(widget, 'Enter a valid ' + describeExpectedLength(range) + ' for ' + countryName + '.');
            return false;
        }
        setError(widget, '');
        return true;
    }

    function selectCountry(widget, country) {
        widget.dataset.iso2 = country.iso2;
        widget.querySelector('.phone-country-flag').src = 'https://flagcdn.com/w20/' + country.iso2 + '.png';
        widget.querySelector('.phone-country-flag').alt = country.name;
        widget.querySelector('.phone-country-dial').textContent = country.code;
        applyLengthConstraints(widget, country);
        syncHidden(widget);
    }

    function buildOptions(widget, countries, listEl) {
        listEl.innerHTML = '';
        countries.forEach(function (country) {
            var li = document.createElement('li');
            li.className = 'phone-country-option';
            li.innerHTML =
                '<img loading="lazy" src="https://flagcdn.com/w20/' + country.iso2 + '.png" alt="">' +
                '<span>' + country.name + '</span>' +
                '<span class="phone-country-option-dial">' + country.code + '</span>';
            li.addEventListener('click', function () {
                selectCountry(widget, country);
                widget.querySelector('.phone-country-select').classList.remove('open');
                widget.querySelector('.phone-number-input').focus();
            });
            listEl.appendChild(li);
        });
    }

    // Given an existing E.164-ish value ("+919876543210"), find the country
    // whose dial code is the longest matching prefix, and split off the
    // local digits — used to prefill the widget when editing a saved number.
    function splitExistingValue(value) {
        var digits = value.replace(/[^\d+]/g, '');
        if (!digits.startsWith('+')) return null;
        var best = null;
        window.COUNTRY_CODES.forEach(function (country) {
            if (digits.startsWith(country.code) && (!best || country.code.length > best.code.length)) {
                best = country;
            }
        });
        if (!best) return null;
        return { country: best, local: digits.slice(best.code.length) };
    }

    function initWidget(widget) {
        var countries = window.COUNTRY_CODES || [];
        var select = widget.querySelector('.phone-country-select');
        var btn = widget.querySelector('.phone-country-btn');
        var menu = widget.querySelector('.phone-country-menu');
        var listEl = widget.querySelector('.phone-country-list');
        var searchInput = widget.querySelector('.phone-country-search');
        var numberInput = widget.querySelector('.phone-number-input');
        var hidden = document.getElementById(widget.dataset.target);

        buildOptions(widget, countries, listEl);

        // Prefill from an existing saved value (profile edit) or fall back
        // to the widget's configured default country (new registration).
        var defaultIso2 = (widget.dataset.defaultCountry || 'in').toLowerCase();
        var existing = hidden && hidden.value ? splitExistingValue(hidden.value) : null;
        if (existing) {
            selectCountry(widget, existing.country);
            numberInput.value = existing.local;
        } else {
            var defaultCountry = countries.find(function (c) { return c.iso2 === defaultIso2; }) || countries[0];
            if (defaultCountry) selectCountry(widget, defaultCountry);
        }
        syncHidden(widget);

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var willOpen = !select.classList.contains('open');
            closeAllMenus(select);
            select.classList.toggle('open', willOpen);
            btn.setAttribute('aria-expanded', String(willOpen));
            if (willOpen) {
                searchInput.value = '';
                buildOptions(widget, countries, listEl);
                setTimeout(function () { searchInput.focus(); }, 0);
            }
        });

        searchInput.addEventListener('click', function (e) { e.stopPropagation(); });
        searchInput.addEventListener('input', function () {
            var q = searchInput.value.trim().toLowerCase();
            var filtered = !q ? countries : countries.filter(function (c) {
                return c.name.toLowerCase().indexOf(q) !== -1 || c.code.indexOf(q) !== -1;
            });
            buildOptions(widget, filtered, listEl);
        });

        numberInput.addEventListener('input', function () {
            var range = lengthRangeFor(widget.dataset.iso2);
            var digits = numberInput.value.replace(/\D/g, '').slice(0, range[1]);
            if (numberInput.value !== digits) numberInput.value = digits;
            syncHidden(widget);
            // onlyIfDirty: before the field's first blur, a too-short number
            // (still being typed) is not flagged as an error — but once
            // `touched` is set, this also clears the error live as digits
            // are fixed, since the valid path always clears regardless.
            validateWidget(widget, { onlyIfDirty: true });
        });

        numberInput.addEventListener('blur', function () {
            widget.dataset.touched = '1';
            validateWidget(widget);
        });
    }

    // One listener per <form>, covering every phone widget inside it (a page
    // can have both "Mobile Number" and "Alternative Mobile"). Blocks
    // submission and focuses the first invalid field — the server's
    // `phonenumbers`-based check (users/forms.py) still re-validates
    // regardless, so this is purely an earlier, friendlier catch.
    function wireFormValidation(widgets) {
        var formsSeen = new Set();
        widgets.forEach(function (widget) {
            var form = widget.closest('form');
            if (!form || formsSeen.has(form)) return;
            formsSeen.add(form);
            form.addEventListener('submit', function (e) {
                var formWidgets = Array.prototype.slice.call(
                    form.querySelectorAll('.phone-input-widget')
                );
                var firstInvalid = null;
                formWidgets.forEach(function (w) {
                    w.dataset.touched = '1';
                    if (!validateWidget(w) && !firstInvalid) firstInvalid = w;
                });
                if (firstInvalid) {
                    e.preventDefault();
                    firstInvalid.querySelector('.phone-number-input').focus();
                }
            });
        });
    }

    function init() {
        if (!window.COUNTRY_CODES) return;
        var widgets = Array.prototype.slice.call(document.querySelectorAll('.phone-input-widget'));
        widgets.forEach(initWidget);
        wireFormValidation(widgets);
        document.addEventListener('click', function () { closeAllMenus(null); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAllMenus(null);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
