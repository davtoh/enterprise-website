/**
 * Navigation Controller
 * Handles Superfish desktop menu, mobile sliding drawer, smooth scrolling, and header scroll state.
 */
window.EnterpriseApp = window.EnterpriseApp || {};

window.EnterpriseApp.Navigation = (function ($) {
    "use strict";

    function initDesktopNav() {
        if (typeof $.fn.superfish === "function") {
            $(".nav-menu").superfish({
                animation: {
                    opacity: "show"
                },
                speed: 400
            });
        }
    }

    function buildMobileNavDOM() {
        var $mobile_nav = $("#nav-menu-container").clone().prop({
            id: "mobile-nav"
        });
        $mobile_nav.find("> ul").attr({
            "class": "",
            "id": ""
        });
        $("body").append($mobile_nav);
        $("body").prepend('<button type="button" id="mobile-nav-toggle"><i class="lnr lnr-menu"></i></button>');
        $("body").append('<div id="mobile-body-overly"></div>');
        $("#mobile-nav").find(".menu-has-children").prepend('<i class="lnr lnr-chevron-down"></i>');
    }

    function bindMobileNavEvents() {
        $(document).on("click", ".menu-has-children i", function (e) {
            $(this).next().toggleClass("menu-item-active");
            $(this).nextAll("ul").eq(0).slideToggle();
            $(this).toggleClass("lnr-chevron-up lnr-chevron-down");
        });

        $(document).on("click", "#mobile-nav-toggle", function (e) {
            $("body").toggleClass("mobile-nav-active");
            $("#mobile-nav-toggle i").toggleClass("lnr-cross lnr-menu");
            $("#mobile-body-overly").toggle();
        });

        $(document).click(function (e) {
            var container = $("#mobile-nav, #mobile-nav-toggle");
            if (!container.is(e.target) && container.has(e.target).length === 0) {
                if ($("body").hasClass("mobile-nav-active")) {
                    $("body").removeClass("mobile-nav-active");
                    $("#mobile-nav-toggle i").toggleClass("lnr-cross lnr-menu");
                    $("#mobile-body-overly").fadeOut();
                }
            }
        });
    }

    function initMobileNav() {
        if ($("#nav-menu-container").length) {
            if (!$("#mobile-nav").length) {
                buildMobileNavDOM();
            }
            bindMobileNavEvents();
        } else if ($("#mobile-nav, #mobile-nav-toggle").length) {
            $("#mobile-nav, #mobile-nav-toggle").hide();
        }
    }

    function initSmoothScroll() {
        $(".nav-menu a, #mobile-nav a, .scrollto").on("click", function () {
            if (location.pathname.replace(/^\//, "") === this.pathname.replace(/^\//, "") && location.hostname === this.hostname) {
                var target = $(this.hash);
                if (target.length) {
                    var top_space = 0;
                    if ($("#header").length) {
                        top_space = $("#header").outerHeight() || 0;
                    }

                    $("html, body").animate({
                        scrollTop: target.offset().top - top_space
                    }, 1500, "easeInOutExpo");

                    if ($(this).parents(".nav-menu").length) {
                        $(".nav-menu .menu-active").removeClass("menu-active");
                        $(this).closest("li").addClass("menu-active");
                    }

                    if ($("body").hasClass("mobile-nav-active")) {
                        $("body").removeClass("mobile-nav-active");
                        $("#mobile-nav-toggle i").toggleClass("lnr-times lnr-bars");
                        $("#mobile-body-overly").fadeOut();
                    }
                    return false;
                }
            }
        });
    }

    function initHashScroll() {
        $("html, body").hide();
        if (window.location.hash && $(window.location.hash).length) {
            setTimeout(function () {
                $("html, body").scrollTop(0).show();
                $("html, body").animate({
                    scrollTop: $(window.location.hash).offset().top - 108
                }, 1000);
            }, 0);
        } else {
            $("html, body").show();
        }
    }

    function initHeaderScrollState() {
        $(window).scroll(function () {
            if ($(this).scrollTop() > 100) {
                $("#header").addClass("header-scrolled");
            } else {
                $("#header").removeClass("header-scrolled");
            }
        });
    }

    function init() {
        initDesktopNav();
        initMobileNav();
        initSmoothScroll();
        initHashScroll();
        initHeaderScrollState();
    }

    return {
        init: init,
        initDesktopNav: initDesktopNav,
        initMobileNav: initMobileNav,
        initSmoothScroll: initSmoothScroll,
        initHashScroll: initHashScroll,
        initHeaderScrollState: initHeaderScrollState
    };
})(jQuery);
