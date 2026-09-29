/* =========================================================
   JOBNEST - JOB JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* SAVE JOB BUTTON */

    const saveButtons =
        document.querySelectorAll("[data-save-job]");

    saveButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const icon = button.querySelector("i");

            if (button.classList.contains("saved")) {

                button.classList.remove("saved");

                if (icon) {
                    icon.className = "fa-regular fa-bookmark";
                }

            } else {

                button.classList.add("saved");

                if (icon) {
                    icon.className = "fa-solid fa-bookmark";
                }

            }

        });

    });


    /* CLEAR FILTERS */

    const clearButton =
        document.querySelector("#clearFilters");

    if (clearButton) {

        clearButton.addEventListener("click", function () {

            const form =
                document.querySelector("#jobFilterForm");

            if (form) {
                form.reset();
            }

        });

    }

});