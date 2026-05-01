/* LumberBank Estimation Tool — base JS */

document.addEventListener('DOMContentLoaded', function () {

  // ── Toast messages ────────────────────────────────────────
  var toasts = document.querySelectorAll('.toast');

  toasts.forEach(function (toast) {
    var timer = setTimeout(function () { dismissToast(toast); }, 4000);

    toast.addEventListener('click', function () {
      clearTimeout(timer);
      dismissToast(toast);
    });
  });

  function dismissToast(el) {
    el.classList.add('toast-hiding');
    setTimeout(function () {
      if (el.parentNode) { el.parentNode.removeChild(el); }
    }, 420);  // slightly longer than the CSS transition
  }

});
