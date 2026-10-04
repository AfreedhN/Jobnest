document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector("#jobSearch");
    const cards = Array.from(document.querySelectorAll(".job-card"));
    const resultCount = document.querySelector("#jobResultCount");
    const liveEmpty = document.querySelector("#jobLiveEmpty");
    const filterForm = document.querySelector("#jobFilterForm");
    const categorySelect = document.querySelector("#jobCategory");
    const workModeSelect = document.querySelector("#jobWorkMode");
    const jobTypeSelect = document.querySelector("#jobType");

    [categorySelect, workModeSelect, jobTypeSelect].forEach(function (select) {
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
            const searchableText = (card.dataset.search || "").toLocaleLowerCase();
            const isMatch = searchableText.includes(query);
            card.hidden = !isMatch;
            matches += isMatch ? 1 : 0;
        });

        if (resultCount) {
            resultCount.textContent = matches;
        }

        if (liveEmpty) {
            liveEmpty.hidden = matches > 0;
        }
    });
});