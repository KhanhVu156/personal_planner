// ============================================================
// main.js - Xử lý tương tác frontend cho Personal Planner
// ============================================================

// Đợi DOM tải xong trước khi gán sự kiện
document.addEventListener('DOMContentLoaded', function() {

    // ----- 1. Cập nhật tiến trình task (AJAX) -----
    // Tìm tất cả các thanh trượt (range input) có class 'task-progress-slider'
    const progressSliders = document.querySelectorAll('.task-progress-slider');
    
    progressSliders.forEach(slider => {
        slider.addEventListener('change', function() {
            const taskId = this.dataset.id;          // Lấy ID task từ data-id
            const progress = parseInt(this.value, 10);
            
            // Gửi request POST đến endpoint update_progress
            fetch(`/tasks/update_progress/${taskId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ progress: progress })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Cập nhật hiển thị phần trăm
                    const progressSpan = document.querySelector(`#task-progress-${taskId}`);
                    if (progressSpan) progressSpan.innerText = progress + '%';
                    
                    // Nếu tiến trình đạt 100%, chuyển trạng thái thành 'Done'
                    if (progress === 100) {
                        const statusSpan = document.querySelector(`#task-status-${taskId}`);
                        if (statusSpan) statusSpan.innerText = 'Done';
                    }
                } else {
                    alert('Cập nhật thất bại: ' + (data.error || 'Lỗi không xác định'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Lỗi kết nối, vui lòng thử lại.');
            });
        });
    });

    // ----- 2. Xác nhận trước khi xóa (dùng cho các nút xóa) -----
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Bạn có chắc chắn muốn xóa mục này không?')) {
                e.preventDefault();
            }
        });
    });

    // ----- 3. Tự động submit form import CSV khi chọn file -----
    const csvInput = document.getElementById('csvInput');
    if (csvInput) {
        csvInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                this.form.submit();
            }
        });
    }

    // ----- 4. Tự động ẩn thông báo flash sau 3 giây -----
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    });

});