// Mask-and-reveal toggle for sensitive ID fields (Aadhaar/PAN/Passport) in
// edit forms — pairs with templates/includes/mask_reveal_field.html.
//
// The masked text is computed server-side (core/mask_utils.py) and the real
// <input> is always rendered empty by the form itself (see
// users/forms.py: ProfileUpdateForm), so this only needs to swap which one
// is visible — no client-side masking logic, and no value is ever read from
// or written to the input, so there's no way for this script to submit the
// masked placeholder in place of a real value.
(function () {
    function initField(wrapper) {
        var displayEl = wrapper.querySelector('.mask-reveal-display');
        var inputWrap = wrapper.querySelector('.mask-reveal-input');
        var toggleBtn = wrapper.querySelector('.mask-reveal-toggle');
        var input = inputWrap ? inputWrap.querySelector('input') : null;
        if (!displayEl || !inputWrap || !toggleBtn || !input) return;

        toggleBtn.addEventListener('click', function () {
            displayEl.classList.add('d-none');
            inputWrap.classList.remove('d-none');
            input.focus();
        });
    }

    function init() {
        document.querySelectorAll('.mask-reveal-field').forEach(initField);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
