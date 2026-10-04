/* =========================================================
   JOBNEST - FORM VALIDATION
   ========================================================= */

window.togglePassword = function (targetId) {
    const input = document.getElementById(targetId);

    if (!input) return;

    const button = input.closest(".input-icon")?.querySelector(".password-toggle");
    const icon = button?.querySelector("i");

    if (input.type === "password") {
        input.type = "text";
        if (icon) icon.className = "fa-solid fa-eye-slash";
    } else {
        input.type = "password";
        if (icon) icon.className = "fa-regular fa-eye";
    }
};

document.addEventListener("DOMContentLoaded", function () {

    const registrationForm =
        document.querySelector("#registrationForm");

    if (registrationForm) {
        const characterFilters = {
            username: /[^\p{L}\p{N}_@.+-]/gu,
            email: /[^\x21-\x7E]/g
        };
        const registrationFields = [
            "first_name",
            "email",
            "username",
            "password",
            "confirm_password",
            "account_type",
            "terms"
        ];
        const touchedFields = new Set();

        function setFieldError(fieldName, message) {
            const field = registrationForm.elements.namedItem(fieldName);
            const error = registrationForm.querySelector(
                '[data-for="' + fieldName + '"]'
            );

            if (!field || !error) return;
            error.textContent = message;
            if (message) {
                field.setAttribute("aria-invalid", "true");
            } else {
                field.removeAttribute("aria-invalid");
            }
        }

        function sanitizeCharacterField(field) {
            const filter = characterFilters[field.name];
            if (!filter) return;

            const sanitizedValue = field.value.replace(filter, "");
            if (sanitizedValue !== field.value) field.value = sanitizedValue;
        }

        [registrationForm.elements.namedItem("username"), registrationForm.elements.namedItem("email")]
            .filter(Boolean)
            .forEach(function (field) {
                const filter = characterFilters[field.name];

                field.addEventListener("beforeinput", function (event) {
                    if (
                        event.isComposing
                        || event.inputType === "insertCompositionText"
                        || !event.inputType.startsWith("insert")
                        || event.data === null
                    ) {
                        return;
                    }

                    if (event.data.replace(filter, "") !== event.data) {
                        event.preventDefault();
                    }
                });

                field.addEventListener("paste", function (event) {
                    const pastedText = event.clipboardData?.getData("text");
                    if (
                        pastedText !== undefined
                        && pastedText.replace(filter, "") !== pastedText
                    ) {
                        event.preventDefault();
                    }
                });

                field.addEventListener("input", function (event) {
                    if (!event.isComposing) sanitizeCharacterField(field);
                });

                field.addEventListener("compositionend", function () {
                    sanitizeCharacterField(field);
                });
            });

        function validateField(fieldName) {
            const field = registrationForm.elements.namedItem(fieldName);
            if (!field) return true;

            let message = "";
            const value = fieldName === "terms"
                ? field.checked
                : field.value.trim();

            if (fieldName === "terms") {
                if (!value) message = "You must agree to the terms and conditions.";
            } else if (!value && fieldName === "password") {
                message = "Password is required.";
            } else if (!value && fieldName === "confirm_password") {
                message = "Please confirm your password.";
            } else if (!value && fieldName === "first_name") {
                message = "First name is required.";
            } else if (!value && fieldName === "email") {
                message = "Email address is required.";
            } else if (!value && fieldName === "username") {
                message = "Username is required.";
            } else if (!value && fieldName === "account_type") {
                message = "Choose an account type.";
            } else if (fieldName === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                message = "Please enter a valid email address.";
            } else if (fieldName === "password" && value.length < 8) {
                message = "Invalid password. Use at least 8 characters.";
            } else if (fieldName === "password" && /^\d+$/.test(value)) {
                message = "Invalid password. It cannot contain only numbers.";
            } else if (
                fieldName === "confirm_password"
                && value !== registrationForm.elements.namedItem("password").value
            ) {
                message = "The passwords do not match.";
            }

            setFieldError(fieldName, message);
            return !message;
        }

        registrationFields.forEach(function (fieldName) {
            const field = registrationForm.elements.namedItem(fieldName);
            if (!field) return;

            const error = registrationForm.querySelector(
                '[data-for="' + fieldName + '"]'
            );
            if (error && error.textContent.trim()) {
                field.setAttribute("aria-invalid", "true");
                touchedFields.add(fieldName);
            }

            field.addEventListener("blur", function () {
                touchedFields.add(fieldName);
                validateField(fieldName);
            });
            field.addEventListener(
                fieldName === "terms" || fieldName === "account_type" ? "change" : "input",
                function () {
                    if (touchedFields.has(fieldName)) {
                        validateField(fieldName);
                    }
                    if (fieldName === "password" && touchedFields.has("confirm_password")) {
                        validateField("confirm_password");
                    }
                }
            );
        });

        registrationForm.addEventListener("submit", function (event) {
            const invalidFields = registrationFields.filter(function (fieldName) {
                touchedFields.add(fieldName);
                return !validateField(fieldName);
            });

            if (invalidFields.length) {
                event.preventDefault();
                registrationForm.elements.namedItem(invalidFields[0]).focus();
            }
        });
    }

    /* PASSWORD MATCH */

    const password =
        document.querySelector("#password");

    const confirmPassword =
        document.querySelector("#confirm_password");

    if (password && confirmPassword) {

        confirmPassword.addEventListener("input", function () {

            if (password.value !== confirmPassword.value) {

                confirmPassword.setCustomValidity(
                    "Passwords do not match."
                );

            } else {

                confirmPassword.setCustomValidity("");

            }

        });

    }


    /* PASSWORD VISIBILITY */

    const toggleButtons =
        document.querySelectorAll(".toggle-password");

    toggleButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const targetId =
                button.dataset.target;

            const input =
                document.getElementById(targetId);

            if (!input) return;

            if (input.type === "password") {

                input.type = "text";

                const icon =
                    button.querySelector("i");

                if (icon) {
                    icon.className = "fa-solid fa-eye-slash";
                }

            } else {

                input.type = "password";

                const icon =
                    button.querySelector("i");

                if (icon) {
                    icon.className = "fa-solid fa-eye";
                }

            }

        });

    });


    /* FILE SIZE VALIDATION */

    const fileInputs =
        document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            const file = input.files[0];

            if (!file) return;

            const maxSize =
                5 * 1024 * 1024;

            if (file.size > maxSize) {

                alert(
                    "File size must be less than 5 MB."
                );

                input.value = "";

            }

        });

    });


    /* EMAIL VALIDATION */

    const emailInputs =
        document.querySelectorAll('input[type="email"]');

    emailInputs.forEach(function (input) {

        input.addEventListener("blur", function () {

            const email =
                input.value.trim();

            const pattern =
                /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (email && !pattern.test(email)) {

                input.setCustomValidity(
                    "Please enter a valid email address."
                );

            } else {

                input.setCustomValidity("");

            }

        });

    });

});