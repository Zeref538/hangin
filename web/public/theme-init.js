// Runs in <head> before the page paints, so there is no flash of the wrong theme.
// Saved choice wins; otherwise follow the system; dark if the system says nothing.
(function () {
  var t = null;
  try { t = localStorage.getItem("theme"); } catch (e) {}
  if (t !== "light" && t !== "dark") {
    t = window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  document.documentElement.setAttribute("data-theme", t);
})();
