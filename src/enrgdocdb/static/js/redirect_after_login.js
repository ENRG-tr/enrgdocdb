document.addEventListener("DOMContentLoaded", () => {
    const isAuthView = !!document.querySelector("[data-is-auth-view='true']");
    const redirectUrlKey = "redirect-after-auth-url";
    if (!isAuthView && localStorage.getItem(redirectUrlKey)) {
        window.location.href = localStorage.getItem(redirectUrlKey);
        localStorage.removeItem(redirectUrlKey);
    }
    if (isAuthView && !["/login", "/register"].includes(window.location.pathname)) {
        // The idea is to catch the page nginx blocks with auth_request and redirect
        // the user to that page after login. When /login or /register is requested
        // that means the user is not here because of the auth_request.
        const redirectUrl = window.location.href;
        localStorage.setItem(redirectUrlKey, redirectUrl);
    }
});