/**
 * main.js — Single source of truth cho toàn bộ interactive behavior.
 *
 * TƯ DUY THIẾT KẾ (Design Thinking):
 * - Event Delegation: Gắn sự kiện vào document.body thay vì từng element. 
 *   Giúp code hoạt động bình thường ngay cả khi DOM bị thay thế (HTMX swap).
 * - IIFE (Hàm tự thực thi): Tránh ô nhiễm không gian tên toàn cục (Global Namespace).
 */
(function () {
    'use strict';

    // ============================================================
    // HELPERS
    // ============================================================
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    // ============================================================
    // 1. DELETE MODAL (Xử lý xóa an toàn qua POST Form)
    // ============================================================
    let pendingDeleteForm = null; // Lưu trữ Form cần submit thay vì URL

    function openDeleteModal(formElement) {
        const modal = document.getElementById('custom-delete-modal');
        if (!modal) {
            // Fallback cho trình duyệt cũ
            if (confirm('Bạn có chắc chắn muốn xóa mục này không?')) {
                formElement.submit();
            }
            return;
        }
        
        pendingDeleteForm = formElement;
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
        pendingDeleteForm = null;
    }

    document.addEventListener('click', function (e) {
        // 1.1. Khi bấm vào nút Xóa (class .delete-confirm)
        const delBtn = e.target.closest('.delete-confirm');
        if (delBtn) {
            e.preventDefault();
            e.stopPropagation();
            
            // ✅ FIX CRITICAL: Tìm form POST chứa nút xóa này (thay vì lấy href)
            const form = delBtn.closest('form.delete-form');
            if (form) {
                openDeleteModal(form);
            } else {
                console.error('[Delete Modal] Không tìm thấy form chứa nút xóa.');
            }
            return;
        }
        
        // 1.2. Nút Hủy trên Modal
        if (e.target.id === 'modal-cancel-btn') {
            e.preventDefault();
            closeDeleteModal();
            return;
        }
        
        // 1.3. Nút Xóa ngay trên Modal
        if (e.target.id === 'modal-confirm-btn') {
            e.preventDefault();
            if (pendingDeleteForm) {
                // ✅ FIX: Submit form (gửi POST) thay vì chuyển hướng URL (GET)
                pendingDeleteForm.submit();
            }
            return;
        }
        
        // 1.4. Click vùng nền đen để đóng modal
        if (e.target.id === 'custom-delete-modal') {
            closeDeleteModal();
        }
    });

    // ============================================================
    // 2. SLIDER TIẾN ĐỘ TASK (AJAX)
    // ============================================================
    document.addEventListener('change', async function (e) {
        const slider = e.target.closest('.task-progress-slider');
        if (!slider) return;

        const taskId = slider.dataset.id;
        const progress = parseInt(slider.value, 10);
        if (!taskId || isNaN(progress)) return;

        // Guard: Tránh gửi nhiều request liên tục nếu user kéo thả nhanh
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

            // Cập nhật UI Text
            const progressSpan = document.querySelector('#task-progress-' + taskId);
            if (progressSpan) progressSpan.textContent = progress + '%';

            // Cập nhật UI Trạng thái (Badge)
            const statusSpan = document.querySelector('#task-status-' + taskId);
            if (statusSpan) {
                if (progress === 100) {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 text-xs font-semibold rounded-full">Đã xong</span>';
                } else if (progress > 0) {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 text-xs font-semibold rounded-full">Đang làm</span>';
                } else {
                    statusSpan.innerHTML = '<span class="px-2 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300 text-xs font-semibold rounded-full">Chờ xử lý</span>';
                }
            }
        } catch (err) {
            console.error('[Task Progress]', err);
        } finally {
            delete slider.dataset.updating;
        }
    });

    // ============================================================
    // 3. CSV AUTO-SUBMIT
    // ============================================================
    document.addEventListener('change', function (e) {
        if (e.target.id !== 'csvInput') return;
        if (!e.target.files || e.target.files.length === 0) return;

        const submitBtn = document.getElementById('csvSubmitBtn');
        if (submitBtn) {
            submitBtn.innerHTML = '<span class="animate-pulse">Đang tải...</span>';
            submitBtn.disabled = true;
        }
        if (e.target.form) e.target.form.submit();
    });

    // ============================================================
    // 4. DỊCH LỖI HTML5 (Tùy chỉnh thông báo mặc định của trình duyệt)
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
                msg.style.transition = 'opacity 0.5s ease-out';
                msg.style.opacity = '0';
                setTimeout(function () { msg.remove(); }, 500);
            }, 3000);
        });
    }

    // ============================================================
    // 6. CHART THEME HOOK (Dark Mode)
    // ============================================================
    window.updateChartTheme = function (isDark) {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = isDark ? '#94a3b8' : '#64748b'; // slate-400 : slate-500
        Chart.defaults.borderColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
        if (window.charts) {
            window.charts.forEach(function (c) {
                try { c.update(); } catch (_) {}
            });
        }
    };

    // ============================================================
    // 7. initApp — Khởi tạo các thành phần tương tác (Dark mode, Menu)
    // ============================================================
    function initApp() {
        const htmlEl = document.documentElement;

        // --- Dark mode toggle ---
        const oldToggle = document.getElementById('darkModeToggle');
        if (oldToggle) {
            if (htmlEl.classList.contains('dark')) oldToggle.checked = true;
            
            // Clone Node để xóa bỏ các Event Listener cũ (chống bind trùng)
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
    // 8. HOOKS — DOMContentLoaded + HTMX
    // ============================================================
    document.addEventListener('DOMContentLoaded', initApp);

    document.addEventListener('htmx:afterSwap', function () {
        initApp();
        // Refresh CSRF token trong hx-headers (đề phòng session bị xoay)
        const metaToken = getCsrfToken();
        if (metaToken) {
            document.body.setAttribute('hx-headers', JSON.stringify({ 'X-CSRFToken': metaToken }));
        }
    });

})();