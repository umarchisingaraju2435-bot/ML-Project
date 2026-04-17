// Auto-refresh notification count every 30 seconds
function refreshNotifCount() {
    fetch('/notifications/count')
        .then(r => r.json())
        .then(data => {
            const badge = document.querySelector('.badge-red');
            if (data.count > 0) {
                if (badge) badge.textContent = data.count;
                else {
                    const btn = document.querySelector('.notif-btn');
                    if (btn) btn.innerHTML = '🔔 <span class="badge-red">' + data.count + '</span>';
                }
            }
        }).catch(() => {});
}
setInterval(refreshNotifCount, 30000);

// Role tab highlight on login page
function setRole(role, el) {
    document.querySelectorAll('.rtab').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
}
