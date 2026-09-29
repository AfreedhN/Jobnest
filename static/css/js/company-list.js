document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector("#companySearch");
    const cards = Array.from(document.querySelectorAll(".company-card"));
    const visibleCount = document.querySelector("#companyVisibleCount");
    const liveEmpty = document.querySelector("#companyLiveEmpty");
    const filterForm = document.querySelector("#companyFilterForm");
    const industrySelect = document.querySelector("#companyIndustry");
    const locationSelect = document.querySelector("#companyLocation");

    [industrySelect, locationSelect].forEach(function (select) {
        if (select) {
            select.addEventListener("change", function () {
                if (filterForm) {
                    filterForm.submit();
                }
            });
        }
    });

    if (!searchInput || cards.length === 0) {
        return;
    }

    searchInput.addEventListener("input", function () {
        const query = searchInput.value.trim().toLocaleLowerCase();
        let matches = 0;

        cards.forEach(function (card) {
            const isMatch = card.textContent.toLocaleLowerCase().includes(query);
            card.hidden = !isMatch;
            matches += isMatch ? 1 : 0;
        });

        if (visibleCount) {
            visibleCount.textContent = matches;
        }

        if (liveEmpty) {
            liveEmpty.hidden = matches > 0;
        }
    });
});