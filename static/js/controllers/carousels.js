/**
 * Carousels Controller
 * Configures and initializes Owl Carousel sliders across agency themes.
 */
window.EnterpriseApp = window.EnterpriseApp || {};

window.EnterpriseApp.Carousels = (function ($) {
    "use strict";

    function initRelatedCarousel() {
        if ($(".active-realated-carusel").length && typeof $.fn.owlCarousel === "function") {
            $(".active-realated-carusel").owlCarousel({
                items: 1,
                loop: true,
                margin: 100,
                dots: true,
                nav: true,
                navText: ["<span class='lnr lnr-arrow-up'></span>", "<span class='lnr lnr-arrow-down'></span>"],
                autoplay: true,
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 1 }
                }
            });
        }
    }

    function initAboutCarousel() {
        if ($(".active-about-carusel").length && typeof $.fn.owlCarousel === "function") {
            $(".active-about-carusel").owlCarousel({
                items: 1,
                loop: true,
                margin: 100,
                nav: true,
                navText: ["<span class='lnr lnr-arrow-up'></span>", "<span class='lnr lnr-arrow-down'></span>"],
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 1 }
                }
            });
        }
    }

    function initReviewCarousel() {
        if ($(".active-review-carusel").length && typeof $.fn.owlCarousel === "function") {
            $(".active-review-carusel").owlCarousel({
                items: 1,
                loop: true,
                autoplay: true,
                margin: 30,
                dots: true
            });
        }
    }

    function initInfoCarousel() {
        if ($(".active-info-carusel").length && typeof $.fn.owlCarousel === "function") {
            $(".active-info-carusel").owlCarousel({
                items: 1,
                loop: true,
                margin: 100,
                dots: true,
                autoplay: true,
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 1 }
                }
            });
        }
    }

    function initTestimonialCarousel() {
        if ($(".active-testimonial").length && typeof $.fn.owlCarousel === "function") {
            $(".active-testimonial").owlCarousel({
                items: 2,
                loop: true,
                margin: 30,
                dots: true,
                autoplay: true,
                nav: true,
                navText: ["<span class='lnr lnr-arrow-up'></span>", "<span class='lnr lnr-arrow-down'></span>"],
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 2 }
                }
            });
        }
    }

    function initTestimonialsSlider() {
        if ($(".active-testimonials-slider").length && typeof $.fn.owlCarousel === "function") {
            $(".active-testimonials-slider").owlCarousel({
                items: 3,
                loop: true,
                margin: 30,
                dots: true,
                autoplay: true,
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 2 },
                    801: { items: 3 }
                }
            });
        }
    }

    function initFixedSlider() {
        if ($(".active-fixed-slider").length && typeof $.fn.owlCarousel === "function") {
            $(".active-fixed-slider").owlCarousel({
                items: 3,
                loop: true,
                dots: true,
                nav: true,
                navText: ["<span class='lnr lnr-arrow-up'></span>", "<span class='lnr lnr-arrow-down'></span>"],
                responsive: {
                    0: { items: 1 },
                    480: { items: 1 },
                    768: { items: 2 },
                    900: { items: 3 }
                }
            });
        }
    }

    function init() {
        initRelatedCarousel();
        initAboutCarousel();
        initReviewCarousel();
        initInfoCarousel();
        initTestimonialCarousel();
        initTestimonialsSlider();
        initFixedSlider();
    }

    return {
        init: init,
        initRelatedCarousel: initRelatedCarousel,
        initAboutCarousel: initAboutCarousel,
        initReviewCarousel: initReviewCarousel,
        initInfoCarousel: initInfoCarousel,
        initTestimonialCarousel: initTestimonialCarousel,
        initTestimonialsSlider: initTestimonialsSlider,
        initFixedSlider: initFixedSlider
    };
})(jQuery);

