/**
 * Layout Controller
 * Handles viewport fitting, select enhancements, image/video popups, and numerical counters.
 */
window.EnterpriseApp = window.EnterpriseApp || {};

window.EnterpriseApp.Layout = (function ($) {
    "use strict";

    function initViewportDimensions() {
        var window_height = window.innerHeight,
            header_height = $(".default-header").height() || 0,
            fitscreen = window_height - header_height;

        $(".fullscreen").css("height", window_height);
        $(".fitscreen").css("height", fitscreen);
    }

    function initSelectDropdowns() {
        if (typeof $.fn.niceSelect === "function") {
            if (document.getElementById("default-select") || document.getElementById("service-select")) {
                $("select").niceSelect();
            }
        }
    }

    function initPopups() {
        if (typeof $.fn.magnificPopup === "function") {
            $(".img-gal").magnificPopup({
                type: "image",
                gallery: {
                    enabled: true
                }
            });

            $(".play-btn").magnificPopup({
                type: "iframe",
                mainClass: "mfp-fade",
                removalDelay: 160,
                preloader: false,
                fixedContentPos: false
            });
        }
    }

    function initCounters() {
        if (typeof $.fn.counterUp === "function") {
            $(".counter").counterUp({
                delay: 10,
                time: 1000
            });
        }
    }

    function init() {
        initViewportDimensions();
        initSelectDropdowns();
        initPopups();
        initCounters();
    }

    return {
        init: init,
        initViewportDimensions: initViewportDimensions,
        initSelectDropdowns: initSelectDropdowns,
        initPopups: initPopups,
        initCounters: initCounters
    };
})(jQuery);

