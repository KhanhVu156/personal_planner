document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // 1. Xử lý Custom Modal Xóa
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    const modal = document.getElementById('custom-delete-modal');
    const modalCancel = document.getElementById('modal-cancel-btn');
    const modalConfirm = document.getElementById('modal-confirm-btn');
    let deleteUrl = '';

    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            deleteUrl = this.getAttribute('href'); // Lấy link xóa
            if (modal) {
                modal.classList.remove('hidden');
                modal.querySelector('div').classList.add('scale-100');
                modal.querySelector('div').classList.remove('scale-95');
            }
        });
    });

    if (modalCancel) {
        modalCancel.addEventListener('click', () => {
            modal.classList.add('hidden');
            modal.querySelector('div').classList.remove('scale-100');
            modal.querySelector('div').classList.add('scale-95');
        });
    }

    if (modalConfirm) {
        modalConfirm.addEventListener('click', () => {
            if (deleteUrl) window.location.href = deleteUrl;
        });
    }

    // 2. Dịch thông báo lỗi HTML5 sang tiếng Việt
    const requiredInputs = document.querySelectorAll('input[required], select[required], textarea[required]');
    requiredInputs.forEach(input => {
        input.addEventListener('invalid', function(e) {
            e.target.setCustomValidity('Vui lòng điền vào trường này.');
        });
        input.addEventListener('input', function(e) {
            e.target.setCustomValidity('');
        });
    });

    // 3. Xử lý thanh trượt Task (AJAX)
    const progressSliders = document.querySelectorAll('.task-progress-slider');
    progressSliders.forEach(slider => {
        slider.addEventListener('change', function() {
            const taskId = this.dataset.id;
            const progress = parseInt(this.value, 10);
            fetch(`/tasks/update_progress/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ progress: progress })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    const progressSpan = document.querySelector(`#task-progress-${taskId}`);
                    if (progressSpan) progressSpan.innerText = progress + '%';
                    
                    const statusSpan = document.querySelector(`#task-status-${taskId}`);
                    if (statusSpan) {
                        if (progress === 100) statusSpan.innerHTML = '<span class="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">Đã xong</span>';
                        else if (progress > 0 && progress < 100) statusSpan.innerHTML = '<span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">Đang làm</span>';
                        else statusSpan.innerHTML = '<span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full">Chờ xử lý</span>';
                    }
                }
            });
        });
    });

    // 4. Import CSV Loading
    const csvInput = document.getElementById('csvInput');
    if (csvInput) {
        csvInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const submitBtn = document.getElementById('csvSubmitBtn');
                if (submitBtn) {
                    submitBtn.innerHTML = 'Đang tải...';
                    submitBtn.disabled = true;
                }
                this.form.submit();
            }
        });
    }

    // 5. Tự ẩn thông báo Flash Message
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => { msg.style.opacity = '0'; setTimeout(() => msg.remove(), 500); }, 3000);
    });

    // 6. Cập nhật màu Chart khi đổi Dark Mode
    window.updateChartTheme = function(isDark) {
        if (typeof Chart === 'undefined') return;
        Chart.defaults.color = isDark ? '#f9fafb' : '#374151';
        Chart.defaults.borderColor = isDark ? '#374151' : '#e5e7eb';
        if (window.charts) window.charts.forEach(chart => chart.update());
    };
});