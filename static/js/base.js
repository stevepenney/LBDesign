/* LumberBank Estimation Tool — base JS */

function dismissToast(el) {
  el.classList.add('toast-hiding');
  setTimeout(function () {
    if (el.parentNode) { el.parentNode.removeChild(el); }
  }, 420);
}

window.showToast = function (msg, type) {
  type = type || 'info';
  var tray = document.getElementById('toast-tray');
  if (!tray) {
    tray = document.createElement('ul');
    tray.className = 'toast-tray';
    tray.id = 'toast-tray';
    document.body.appendChild(tray);
  }
  var li = document.createElement('li');
  li.className = 'toast ' + type;
  li.textContent = msg;
  tray.appendChild(li);
  var timer = setTimeout(function () { dismissToast(li); }, 4000);
  li.addEventListener('click', function () { clearTimeout(timer); dismissToast(li); });
};

document.addEventListener('DOMContentLoaded', function () {

  // ── Toast messages ────────────────────────────────────────
  document.querySelectorAll('.toast').forEach(function (toast) {
    var timer = setTimeout(function () { dismissToast(toast); }, 4000);
    toast.addEventListener('click', function () { clearTimeout(timer); dismissToast(toast); });
  });

});
