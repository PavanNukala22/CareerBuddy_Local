// Live password requirements checklist — pairs with
// templates/includes/password_requirements.html.
//
// Mirrors the server-side rules (users/password_validators.py plus Django's
// MinimumLength/Common/Numeric validators) so the user can see every rule and
// watch each one tick green as they type, rather than submitting and getting
// back a single message like "This password is too common."
//
// The server remains the authority — this is presentation only.
(function () {
    // Django's CommonPasswordValidator uses a ~20k entry list, which is far
    // too large to ship to the browser. This is the small high-frequency
    // subset that people actually try, so the "Avoid common passwords" rule
    // gives useful live feedback; anything this misses is still caught
    // server-side on submit.
    var COMMON_PASSWORDS = [
        'password', 'password1', 'password123', 'passw0rd', 'p@ssword', 'p@ssw0rd',
        '12345678', '123456789', '1234567890', '123123123', '111111111', '000000000',
        'qwerty', 'qwerty123', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1qaz2wsx',
        'iloveyou', 'admin123', 'welcome1', 'welcome123', 'letmein', 'letmein123',
        'football', 'baseball', 'sunshine', 'princess', 'dragon123', 'monkey123',
        'abc12345', 'abcd1234', 'trustno1', 'superman', 'starwars', 'whatever',
        'computer', 'internet', 'samsung1', 'michael1', 'jennifer', 'nicole123'
    ];

    var SPECIAL_CHAR_RE = /[^A-Za-z0-9\s]/;

    // Passwords are exactly 8 characters: Django's MinimumLengthValidator sets
    // the floor and MaximumLengthValidator (users/password_validators.py) the
    // ceiling, with maxlength="8" on the inputs stopping longer input outright.
    var PASSWORD_LENGTH = 8;

    var RULES = {
        length:  function (v) { return v.length === PASSWORD_LENGTH; },
        upper:   function (v) { return /[A-Z]/.test(v); },
        lower:   function (v) { return /[a-z]/.test(v); },
        number:  function (v) { return /[0-9]/.test(v); },
        special: function (v) { return SPECIAL_CHAR_RE.test(v); },
        common:  function (v) {
            var lower = v.toLowerCase();
            // Flag an exact match or a common password padded with a couple of
            // trailing characters ("password1!"), which is the usual dodge and
            // is what Django's list-based check rejects too.
            return !COMMON_PASSWORDS.some(function (common) {
                return lower === common || (lower.indexOf(common) === 0 && lower.length - common.length <= 2);
            });
        }
    };

    function updateList(listEl, value) {
        var touched = value.length > 0;
        listEl.querySelectorAll('li[data-rule]').forEach(function (li) {
            var check = RULES[li.dataset.rule];
            if (!check) return;
            // An untouched field reads as neutral guidance rather than a list
            // of passes and failures, so nothing is marked met or unmet until
            // the user actually starts typing. Without this the "Avoid common
            // passwords" rule would show as already satisfied on an empty
            // field, while every other rule showed as pending.
            var met = touched && check(value);
            var icon = li.querySelector('.pw-req-icon');

            li.classList.toggle('pw-req-met', met);
            li.classList.toggle('pw-req-unmet-active', touched && !met);
            if (icon) icon.textContent = touched ? (met ? '✔' : '✘') : '○';
        });
    }

    function init() {
        document.querySelectorAll('.pw-req-list[data-pw-target]').forEach(function (listEl) {
            var input = document.getElementById(listEl.dataset.pwTarget);
            if (!input) return;
            input.addEventListener('input', function () { updateList(listEl, input.value); });
            // Reflect any value already present (e.g. browser autofill, or a
            // re-render after a failed submit).
            updateList(listEl, input.value);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
