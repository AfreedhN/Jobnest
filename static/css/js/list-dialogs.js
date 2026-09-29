document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-open-dialog]").forEach(function (trigger) {
        trigger.addEventListener("click", function () {
            const dialog = document.getElementById(trigger.dataset.openDialog);
            if (dialog && !dialog.open) dialog.showModal();
        });
    });

    document.querySelectorAll(".listing-dialog").forEach(function (dialog) {
        if (dialog.dataset.reopen === "true") dialog.showModal();

        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) dialog.close();
        });

        dialog.querySelectorAll("[data-close-dialog]").forEach(function (button) {
            button.addEventListener("click", function () {
                dialog.close();
            });
        });
    });
});
