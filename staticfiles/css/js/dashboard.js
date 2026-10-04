/* =========================================================
   JOBNEST - DASHBOARD JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* SIDEBAR ACTIVE MENU */

    const menuLinks =
        document.querySelectorAll(".dashboard-menu a");

    menuLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            menuLinks.forEach(function (item) {
                item.classList.remove("active");
            });

            link.classList.add("active");

        });

    });


    /* APPLICATION STATUS FILTER */

    const statusFilter =
        document.querySelector("#statusFilter");

    const applicationRows =
        document.querySelectorAll(
            "[data-application-status]"
        );

    if (statusFilter && applicationRows.length > 0) {

        statusFilter.addEventListener("change", function () {

            const selected =
                statusFilter.value;

            applicationRows.forEach(function (row) {

                const status =
                    row.dataset.applicationStatus;

                if (!selected || selected === status) {

                    row.style.display = "";

                } else {

                    row.style.display = "none";

                }

            });

        });

    }


    /* DELETE JOB CONFIRMATION */

    const deleteJobButtons =
        document.querySelectorAll(".delete-job");

    deleteJobButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const confirmed =
                confirm(
                    "Are you sure you want to delete this job?"
                );

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });


    /* STATUS CHANGE CONFIRMATION */

    const statusForms =
        document.querySelectorAll(".status-form");

    statusForms.forEach(function (form) {

        form.addEventListener("submit", function (event) {

            const select =
                form.querySelector("select");

            if (!select) return;

            const status =
                select.value;

            if (
                status === "rejected" &&
                !confirm(
                    "Are you sure you want to reject this application?"
                )
            ) {

                event.preventDefault();

            }

        });

    });

});