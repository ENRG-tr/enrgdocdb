document.addEventListener("DOMContentLoaded", () => {
    const isAuthView = !!document.querySelector("[data-is-auth-view='true']");
    const isLegitAuthURL = ["/login", "/register"].includes(window.location.pathname);
    const redirectUrlKey = "redirect-after-auth-url";
    if (!isAuthView && localStorage.getItem(redirectUrlKey)) {
        window.location.href = localStorage.getItem(redirectUrlKey);
        localStorage.removeItem(redirectUrlKey);
    }
    if (isAuthView) {
        if (!isLegitAuthURL) {
            // The idea is to catch the page nginx blocks with auth_request and redirect
            // the user to that page after login. When /login or /register is requested
            // that means the user is not here because of the auth_request.
            const redirectUrl = window.location.href;
            localStorage.setItem(redirectUrlKey, redirectUrl)
        } else {
            // Display a info message to say that they need to login before they can see this page
            const infoMessage = document.createElement("div");
            infoMessage.classList.add("alert", "alert-info");
            infoMessage.innerHTML = "You need to login with your ENRG DocDB account before you can see this page. (Presumably ENRGDAQ or its data)";
            // Add it after h1
            document.querySelector("h1").parentNode.insertBefore(infoMessage, document.querySelector("h1").nextSibling);
        }
    }
});