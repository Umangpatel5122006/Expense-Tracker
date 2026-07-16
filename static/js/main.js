// main.js — students will add JavaScript here as features are built

// --------------------------------------------------------------------- //
// Category distribution chart — hover/focus tooltip                     //
// --------------------------------------------------------------------- //
//
// Each row in `.category-chart` already carries an `aria-label` with the
// full info (category name, percent, amount), so screen readers get the
// data without JS. This module adds an *optional* visual tooltip for
// sighted users on hover/focus. The tooltip is a single shared element
// appended to <body> and absolutely positioned to the active row. It
// dismisses on mouseleave, blur, scroll, and Escape.
//
// No external dependencies. Idempotent — safe to load on every page.

(function () {
    "use strict";

    function init() {
        var chart = document.querySelector(".category-chart");
        if (!chart) return;

        var rows = chart.querySelectorAll(".chart-row");
        if (rows.length === 0) return;

        var tooltip = document.createElement("div");
        tooltip.className = "chart-tooltip";
        tooltip.setAttribute("role", "tooltip");
        tooltip.hidden = true;
        document.body.appendChild(tooltip);

        var activeRow = null;

        function show(row) {
            if (activeRow === row) return;
            activeRow = row;
            var label = row.querySelector(".chart-row-label");
            var pct = row.querySelector(".chart-row-pct");
            tooltip.textContent = (label ? label.textContent : "") +
                                  " — " +
                                  (pct ? pct.textContent : "");
            tooltip.hidden = false;
            // Position below the row, centred on the bar area.
            var rect = row.getBoundingClientRect();
            var tipRect = tooltip.getBoundingClientRect();
            var top = window.scrollY + rect.bottom + 8;
            var left = window.scrollX + rect.left +
                       (rect.width - tipRect.width) / 2;
            // Keep the tooltip inside the viewport horizontally.
            var maxLeft = window.scrollX + window.innerWidth - tipRect.width - 8;
            if (left > maxLeft) left = maxLeft;
            if (left < window.scrollX + 8) left = window.scrollX + 8;
            tooltip.style.top = top + "px";
            tooltip.style.left = left + "px";
        }

        function hide() {
            tooltip.hidden = true;
            activeRow = null;
        }

        rows.forEach(function (row) {
            row.addEventListener("mouseenter", function () { show(row); });
            row.addEventListener("mouseleave", hide);
            row.addEventListener("focus", function () { show(row); });
            row.addEventListener("blur", hide);
        });

        document.addEventListener("scroll", hide, true);
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") hide();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
