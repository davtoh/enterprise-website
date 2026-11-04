/**
 * Enterprise Website - Frontend Orchestrator Facade
 * Coordinates modular controllers for layout, navigation, carousels, and external integrations.
 */
window.EnterpriseApp = window.EnterpriseApp || {};

(function ($) {
    "use strict";

    function bootstrap() {
        if (window.EnterpriseApp.Layout && typeof window.EnterpriseApp.Layout.init === "function") {
            window.EnterpriseApp.Layout.init();
        }
        if (window.EnterpriseApp.Navigation && typeof window.EnterpriseApp.Navigation.init === "function") {
            window.EnterpriseApp.Navigation.init();
        }
        if (window.EnterpriseApp.Carousels && typeof window.EnterpriseApp.Carousels.init === "function") {
            window.EnterpriseApp.Carousels.init();
        }
        if (window.EnterpriseApp.Integrations && typeof window.EnterpriseApp.Integrations.init === "function") {
            window.EnterpriseApp.Integrations.init();
        }
    }

    $(document).ready(function () {
        bootstrap();
    });

    window.EnterpriseApp.bootstrap = bootstrap;
})(jQuery);
