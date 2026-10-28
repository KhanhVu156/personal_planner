/**
 * main.js — Single source of truth cho toàn bộ interactive behavior.
 *
 * Triết lý:
 *  - Event delegation ở document.body (sống qua mọi HTMX swap)
 *  - initApp() chạy cả lần đầu (DOMContentLoaded) và sau swap (htmx:afterSwap)
 *  - Không bind trực tiếp vào element, không dùng DOMContentLoaded cho element-level
 */
(function () {
    'use strict';

    // ============================================================
    // HELPERS
    // ============================================================
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    function escapeHtml(str) {
        return String(str ?? '').replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    // ============================================================
    // 1. DELETE MODAL (delegation)
    // ============================================================
    let pendingDeleteUrl = '';

    function openDeleteModal(url) {
        const modal = document.getElementById('custom-delete-modal');
        if (!modal) {
            if (confirm('Bạn có chắc chắn muốn xóa mục này?')) window.location.href = url;
            return;
        }
        pendingDeleteUrl = url;
        modal.classList.remove('hidden');
        const inner = modal.querySelector('div');
        if (inner) {
            inner.classList.add('scale-100');
            inner.classList.remove('scale-95');
        }
    }

    function closeDeleteModal() {
        const modal = document.getElementById('custom-delete-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        const inner = modal.querySelector('div');
        if (inner) {
            inner.classList.remove('scale-100');
            inner.classList.add('scale-95');
        }
        pendingDeleteUrl = '';
    }

    document.addEventListener('click', function (e) {
        const delBtn = e.target.closest('.delete-confirm');
        if (delBtn) {
            e.preventDefault();
            e.stopPropagation();
            openDeleteModal(delBtn.getAttribute('href') || '');
            return;
        }
        if (e.target.id === 'modal-cancel-btn') {
            e.preventDefault();
            closeDeleteModal();
            return;
        }
        if (e.target.id === 'modal-confirm-btn') {
            e.preventDefault();
            if (pendingDeleteUrl) window.location.href = pendingDeleteUrl;
            return;
        }
        if (e.target.id === 'custom-delete-modal') {
            closeDeleteModal();
        }
    });

    // ============================================================
    // 2. SLIDER TIẾN ĐỘ TASK (delegation)
    // ============================================================
    document.addEventListener('change', async function (e) {
        const slider = e.target.closest('.task-progress-slider');
        if (!slider) return;

        const taskId = slider.dataset.id;
        const progress = parseInt(slider.value, 10);
        if (!taskId || isNaN(progress)) return;

        // Guard: tránh spam nếu kéo liên tục (HTMX/JS đôi khi trigger change 2 lần)
        if (slider.dataset.updating === '1') return;
        slider.dataset.updating = '1';

        try {
            const res = await fetch('/tasks/update_progress/' + taskId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ progress: progress })
            });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();
            if (!data.success) return;

            const progressSpan = document.querySelector('#task-progress-' + taskId);
            if (progressSpan) progressSpan.textContent = progress + '%';

            const statusSpan = document.querySelector('#task-status-' + taskId);
            if (statusSpan) {
                if (progress === 100) {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">Đã xong</span>';
                } else if (progress > 0) {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">Đang làm</span>';
                } else {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full">Chờ xử lý</span>';
                }
            }
        } catch (err) {
            console.error('[Task Progress]', err);
        } finally {
            delete slider.dataset.updating;
        }
    });

    // ============================================================
    // 3. CSV AUTO-SUBMIT (delegation)
    // ============================================================
    document.addEventListener('change', function (e) {
        if (e.target.id !== 'csvInput') return;
        if (!e.target.files || e.target.files.length === 0) return;

        const submitBtn = document.getElementById('csvSubmitBtn');
        if (submitBtn) {
            submitBtn.textContent = 'Đang tải...';
            submitBtn.disabled = true;
        }
        if (e.target.form) e.target.form.submit();
    });

    // ============================================================
    // 4. DỊCH LỖI HTML5 (capture phase)
    // ============================================================
    document.addEventListener('invalid', function (e) {
        if (e.target && e.target.setCustomValidity) {
            e.target.setCustomValidity('Vui lòng điền vào trường này.');
        }
    }, true);

    document.addEventListener('input', function (e) {
        if (e.target && e.target.setCustomValidity) {
            e.target.setCustomValidity('');
        }
    }, true);

    // ============================================================
    // 5. FLASH MESSAGE AUTO-HIDE
    // ============================================================
    function autoHideFlash() {
        document.querySelectorAll('.flash-message:not([data-auto-hide])').forEach(function (msg) {
            msg.setAttribute('data-auto-hide', '1');
            setTimeout(function () {
                msg.style.transition = 'opacity 0.5s';
                msg.style.opacity = '0';
                setTimeout(function () { msg.remove(); }, 500);
            }, 3000);
        });
    }

    // ============================================================
    // 6. CHART THEME HOOK
    // ============================================================
    window.updateChartTheme = function (isDark) {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = isDark ? '#f9fafb' : '#374151';
        Chart.defaults.borderColor = isDark ? '#374151' : '#e5e7eb';
        if (window.charts) {
            window.charts.forEach(function (c) {
                try { c.update(); } catch (_) {}
            });
        }
    };

    // ============================================================
    // 7. initApp — dark mode toggle + mobile menu (rebind sau swap)
    // ============================================================
    function initApp() {
        const htmlEl = document.documentElement;

        // --- Dark mode toggle ---
        const oldToggle = document.getElementById('darkModeToggle');
        if (oldToggle) {
            // Reset về đúng state hiện tại
            if (htmlEl.classList.contains('dark')) oldToggle.checked = true;
            // Clone để xoá hết listener cũ (tránh bind đôi sau swap)
            const newToggle = oldToggle.cloneNode(true);
            oldToggle.replaceWith(newToggle);
            newToggle.addEventListener('change', function (e) {
                const isDark = e.target.checked;
                if (isDark) {
                    htmlEl.classList.add('dark');
                    localStorage.setItem('darkMode', 'enabled');
                } else {
                    htmlEl.classList.remove('dark');
                    localStorage.setItem('darkMode', 'disabled');
                }
                if (window.updateChartTheme) window.updateChartTheme(isDark);
            });
        }

        // --- Mobile menu ---
        const oldBtn = document.getElementById('mobileMenuBtn');
        const mobileMenu = document.getElementById('mobileMenu');
        if (oldBtn && mobileMenu) {
            const newBtn = oldBtn.cloneNode(true);
            oldBtn.replaceWith(newBtn);
            newBtn.addEventListener('click', function () {
                mobileMenu.classList.toggle('hidden');
            });
        }

        autoHideFlash();
    }

    // ============================================================
    // 8. HOOKS — DOMContentLoaded + htmx:afterSwap
    // ============================================================
    document.addEventListener('DOMContentLoaded', initApp);

    document.addEventListener('htmx:afterSwap', function () {
        initApp();
        // Refresh CSRF token trong hx-headers sau khi swap
        // (login/register xoay session → token trong meta đổi)
        const metaToken = getCsrfToken();
        if (metaToken) {
            document.body.setAttribute('hx-headers', JSON.stringify({ 'X-CSRFToken': metaToken }));
        }
    });

    // ============================================================
    // 9. Export helpers cho template
    // ============================================================
    window.appHelpers = {
        escapeHtml: escapeHtml,
        getCsrfToken: getCsrfToken
    };
})();