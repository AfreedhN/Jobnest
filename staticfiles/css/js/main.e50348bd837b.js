/* =========================================================
   JOBNEST - MAIN JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* MOBILE MENU */

    const menuToggle = document.querySelector(".menu-toggle");
    const navLinks = document.querySelector(".nav-links");

    if (menuToggle && navLinks) {

        menuToggle.addEventListener("click", function () {
            const isExpanded = navLinks.classList.toggle("mobile-active");
            menuToggle.setAttribute("aria-expanded", String(isExpanded));
        });

    }


    /* AUTO HIDE ALERTS */

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        setTimeout(function () {

            alert.style.opacity = "0";
            alert.style.transform = "translateY(-5px)";

            setTimeout(function () {
                alert.remove();
            }, 300);

        }, 5000);

    });

    function scheduleAccountSuccessDismissal(toast) {
        if (toast.dataset.dismissScheduled) return;
        toast.dataset.dismissScheduled = "true";

        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-5px)";

            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 3000);
    }

    document.querySelectorAll(".message.account-success").forEach(
        scheduleAccountSuccessDismissal
    );

    const successToastObserver = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType !== Node.ELEMENT_NODE) return;

                if (node.matches(".message.account-success")) {
                    scheduleAccountSuccessDismissal(node);
                }

                node.querySelectorAll(".message.account-success").forEach(
                    scheduleAccountSuccessDismissal
                );
            });
        });
    });

    successToastObserver.observe(document.body, {
        childList: true,
        subtree: true
    });


    /* CONFIRM DELETE */

    const deleteButtons = document.querySelectorAll("[data-confirm-delete]");

    deleteButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const message =
                button.dataset.confirmDelete ||
                "Are you sure you want to delete this?";

            if (!confirm(message)) {
                event.preventDefault();
            }

        });

    });


    /* CURRENT YEAR */

    const yearElements = document.querySelectorAll("[data-current-year]");

    yearElements.forEach(function (element) {
        element.textContent = new Date().getFullYear();
    });


    /* SIMPLE SCROLL ANIMATION */

    const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const animatedElements = document.querySelectorAll(".job-card, .company-card, .stat-card");

    if (!prefersReducedMotion && "IntersectionObserver" in window) {

        const observer = new IntersectionObserver(
            function (entries) {

                entries.forEach(function (entry) {

                    if (entry.isIntersecting) {

                        entry.target.style.opacity = "1";
                        entry.target.style.transform = "translateY(0)";

                        observer.unobserve(entry.target);
                    }

                });

            },
            {
                threshold: 0.1
            }
        );

        animatedElements.forEach(function (element) {

            element.style.opacity = "0";
            element.style.transform = "translateY(15px)";
            element.style.transition = "opacity 0.4s ease, transform 0.4s ease";

            observer.observe(element);

            setTimeout(function () {
                element.style.opacity = "1";
                element.style.transform = "translateY(0)";
            }, 600);

        });

    }

});