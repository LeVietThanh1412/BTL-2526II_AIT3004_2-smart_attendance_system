<template>
    <div class="app-container">
        <AdminSidebar />

        <main class="content">
            <TopHeader title="Điểm danh hằng ngày" />

            <div class="checkin-main">
                <div class="camera-card">
                    <div class="card-header">
                        <h2>Điểm danh bằng AI</h2>
                        <div class="status-badge live">{{ isProcessing ? 'Đang xử lý...' : 'Sẵn sàng' }}</div>
                    </div>

                    <div class="video-area">
                        <video ref="videoEl" autoplay playsinline class="video-stream"></video>
                        <canvas ref="canvasEl" style="display: none;"></canvas>
                        <div class="video-live-tag">TRỰC TIẾP</div>
                        <div class="face-frame"></div>
                        <div class="video-camera-info">Camera HD 01</div>
                    </div>

                    <div class="input-group">
                        <label for="studentIdInput">Mã sinh viên <span class="required">*</span></label>
                        <input 
                            id="studentIdInput"
                            v-model="studentId" 
                            type="text" 
                            placeholder="Nhập mã sinh viên (VD: SV001)" 
                            class="student-id-input"
                            :disabled="isProcessing"
                            @keyup.enter="handleCheckIn"
                        />
                    </div>

                    <button class="checkin-btn" :disabled="isProcessing" @click="handleCheckIn">
                        <span>👤</span>
                        {{ isProcessing ? 'Đang nhận diện...' : 'Bắt đầu điểm danh' }}
                    </button>

                    <div v-if="result" class="result-area" :class="resultClass">
                        <div class="result-icon">{{ resultIcon }}</div>
                        <div class="result-info">
                            <h4>{{ result.userName }}</h4>
                            <p class="result-action-label">{{ result.actionLabel }}</p>
                            <p>{{ result.checkInTime }}</p>
                            <div v-if="result.shiftInfo" class="shift-info">
                                Ca học: {{ result.shiftInfo }}
                            </div>
                            <div v-if="result.detailTimes" class="detail-times">
                                <span v-if="result.detailTimes.in">Check-in: <strong>{{ result.detailTimes.in }}</strong></span>
                                <span v-if="result.detailTimes.out"> → Check-out: <strong>{{ result.detailTimes.out }}</strong></span>
                            </div>
                        </div>
                        <div class="result-badges">
                            <div class="result-status" :class="resultStatusClass">{{ result.statusText }}</div>
                            <div v-if="result.isLate" class="late-badge">⚠️ Muộn</div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AdminSidebar from '../admin/AdminSidebar.vue'
import TopHeader from '../admin/TopHeader.vue'
import { submitCheckIn } from '../shared/api'
import { formatTime, formatShortDate } from '../shared/dateUtils'

const videoEl = ref(null)
const canvasEl = ref(null)
const isProcessing = ref(false)
const result = ref(null)

// Khai báo biến reactive để lưu trữ mã sinh viên
const studentId = ref('')

const resultClass = computed(() => {
    if (!result.value) return ''
    if (result.value.isError) return 'error'
    if (result.value.isLate) return 'late'
    return 'success-state'
})

const resultIcon = computed(() => {
    if (!result.value) return ''
    if (result.value.isError) return '❌'
    const action = result.value.actionLabel || ''
    if (action.includes('Check-out')) return '👋'
    return '✅'
})

const resultStatusClass = computed(() => {
    if (!result.value) return ''
    if (result.value.isError) return 'status-error'
    if (result.value.isLate) return 'status-late'
    return 'status-ok'
})

let videoStream = null

// === Bật webcam khi vào trang ===
const startWebcam = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
        alert('Thiết bị không hỗ trợ Camera.')
        return
    }
    try {
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
            audio: false,
        })
        videoEl.value.srcObject = videoStream
    } catch (err) {
        console.error('[v0] Lỗi mở camera:', err.message)
        alert('Không thể truy cập Camera!')
    }
}

// === Chụp ảnh & gửi backend AI ===
const handleCheckIn = async () => {
    if (!videoEl.value || !canvasEl.value) return

    // ========================================================
    // YÊU CẦU 2: CHẶN THAO TÁC GỬI ẢNH NẾU CHƯA CÓ STUDENT_ID HỢP LỆ
    // ========================================================
    if (!studentId.value || !studentId.value.trim()) {
        const now = new Date()
        result.value = {
            userName: 'Lỗi nhập liệu',
            checkInTime: `${formatTime(now)} - ${formatShortDate(now)}`,
            statusText: 'Thiếu mã sinh viên!',
            isError: true,
        }
        // Tự động focus lại vào ô nhập cho người dùng
        document.getElementById('studentIdInput')?.focus()
        return
    }

    isProcessing.value = true
    result.value = null

    const video = videoEl.value
    const canvas = canvasEl.value
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
    const base64 = canvas.toDataURL('image/jpeg', 0.9)

    try {
        // ========================================================
        // YÊU CẦU 3: GỬI STUDENT_ID KÈM THEO ẢNH LÊN BACKEND
        // ========================================================
        // Truyền cả base64 ảnh và student_id (đã xóa khoảng trắng thừa) vào hàm API
        const res = await submitCheckIn(base64, studentId.value.trim())
        
        const now = new Date()
        const action = res.action // 'check_in' | 'check_out'
        const isLate = res.is_late === true
        const isError = res.status !== 'success' || !res.matched

        // Label hành động
        let actionLabel = ''
        let statusText = ''
        if (action === 'check_in') {
            actionLabel = isLate ? '↗️ Check-in (Muộn)' : '↗️ Check-in'
            statusText = isError ? 'Thất bại' : (isLate ? 'Vào muộn' : 'Vào đúng giờ')
        } else if (action === 'check_out') {
            actionLabel = '↘️ Check-out'
            statusText = isError ? 'Thất bại' : 'Ra về'
        } else {
            statusText = isError ? 'Thất bại' : 'Thành công'
        }

        result.value = {
            userName: res.student_name ? `SV: ${res.student_name}` : `Mã SV: ${studentId.value.trim()}`,
            checkInTime: `${formatTime(now)} - ${formatShortDate(now)}`,
            actionLabel,
            statusText,
            isError,
            isLate,
            shiftInfo: (res.shift_start && res.shift_end) ? `${res.shift_start} – ${res.shift_end}` : null,
            detailTimes: (res.check_in_time || res.check_out_time) ? {
                in: res.check_in_time,
                out: res.check_out_time,
            } : null,
            message: res.message,
        }

        // Điểm danh thành công thì có thể xóa trống ô nhập (tùy chọn)
        // studentId.value = ''

    } catch (err) {
        console.error('[v0] Lỗi gửi điểm danh:', err.message)
        const now = new Date()
        
        // YÊU CẦU 4: Đọc chi tiết thông báo lỗi từ Backend trả về (Ví dụ: Không tồn tại, Điểm thấp...)
        const backendErrorMessage = err?.response?.data?.message || err?.response?.data?.detail || 'Không thể kết nối máy chủ điểm danh.'
        
        result.value = {
            userName: 'Điểm danh thất bại',
            checkInTime: `${formatTime(now)} - ${formatShortDate(now)}`,
            statusText: backendErrorMessage, // Hiển thị rõ lỗi cụ thể lên màn hình
            isError: true,
        }
    } finally {
        isProcessing.value = false
    }
}

onMounted(() => {
    startWebcam()
})

onUnmounted(() => {
    if (videoStream) videoStream.getTracks().forEach((t) => t.stop())
})
</script>

<style scoped>
.app-container {
    display: flex;
    width: 100%;
    min-height: 100vh;
    overflow: hidden;
}

main.content {
    flex-grow: 1;
    padding: 25px 30px;
    overflow-y: auto;
}

.checkin-main {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px 0 40px;
}

.camera-card {
    background: var(--card-color);
    border-radius: 20px;
    padding: 30px;
    width: 100%;
    max-width: 600px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    border: 1px solid var(--border-color);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.card-header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
}

.status-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 20px;
    background-color: #ecfdf5;
    color: var(--success-color);
    font-size: 12px;
    font-weight: 600;
}

.status-badge.live::before {
    content: '';
    width: 8px;
    height: 8px;
    background-color: var(--success-color);
    border-radius: 50%;
}

.video-area {
    position: relative;
    border-radius: 14px;
    overflow: hidden;
    height: 400px;
    background-color: #1a1d21;
    margin-bottom: 20px;
}

.video-stream {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.video-live-tag {
    position: absolute;
    top: 14px;
    left: 14px;
    background-color: var(--danger-color);
    color: white;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 0.5px;
}

.face-frame {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 200px;
    height: 250px;
    border: 3px solid var(--success-color);
    border-radius: 20px;
}

.video-camera-info {
    position: absolute;
    bottom: 12px;
    left: 14px;
    color: #e2e8f0;
    font-size: 11px;
    background-color: rgba(0, 0, 0, 0.5);
    padding: 4px 10px;
    border-radius: 4px;
}

/* --- Thêm CSS mới cho Ô Nhập Mã Sinh Viên --- */
.input-group {
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    text-align: left;
}

.input-group label {
    font-size: 14px;
    font-weight: 600;
    color: #2a3a4e; /* Màu chữ chính phối hợp theo template */
}

.input-group label .required {
    color: var(--danger-color);
}

.student-id-input {
    width: 100%;
    padding: 14px;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    font-size: 15px;
    outline: none;
    box-sizing: border-box;
    transition: border-color 0.2s, box-shadow 0.2s;
    background-color: #f8fafc;
}

.student-id-input:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.15);
    background-color: #ffffff;
}

.student-id-input:disabled {
    background-color: #e2e8f0;
    cursor: not-allowed;
    opacity: 0.7;
}

.checkin-btn {
    width: 100%;
    background-color: var(--primary-color);
    color: white;
    border: none;
    padding: 16px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    transition: background-color 0.2s;
    margin-bottom: 16px;
}

.checkin-btn:hover:not(:disabled) {
    background-color: #314bdc;
}

.checkin-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}

.result-area {
    background-color: #f0fdf4;
    border: 1px solid #d1fae5;
    border-radius: 12px;
    padding: 18px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}

.result-area.error {
    background-color: #fef2f2;
    border-color: #fecaca;
}

.result-area.late {
    background-color: #fffbeb;
    border-color: #fde68a;
}

.result-icon {
    font-size: 24px;
    flex-shrink: 0;
    margin-top: 2px;
}

.result-action-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--primary-color);
    margin: 2px 0 4px;
}

.shift-info {
    font-size: 12px;
    color: var(--text-sub);
    margin-top: 4px;
}

.detail-times {
    font-size: 12px;
    color: var(--text-sub);
    margin-top: 4px;
}

.result-badges {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    flex-shrink: 0;
}

.result-status {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
}

.result-status.status-ok {
    background-color: #ecfdf5;
    color: var(--success-color);
}

.result-status.status-late {
    background-color: #fef3c7;
    color: #92400e;
}

.result-status.status-error {
    background-color: #fee2e2;
    color: var(--danger-color);
}

.late-badge {
    padding: 4px 10px;
    border-radius: 20px;
    background-color: #fef3c7;
    color: #92400e;
    font-size: 11px;
    font-weight: 600;
}

.result-info {
    flex-grow: 1;
}

.result-info h4 {
    margin: 0 0 4px;
    font-size: 16px;
    font-weight: 600;
}

.result-info p {
    margin: 0;
    color: var(--text-sub);
    font-size: 13px;
}

.result-status {
    padding: 6px 12px;
    border-radius: 20px;
    background-color: #ecfdf5;
    color: var(--success-color);
    font-size: 12px;
    font-weight: 600;
}

.result-area.error .result-status {
    background-color: #fee2e2;
    color: var(--danger-color);
}

@media (max-width: 900px) {
    .app-container {
        flex-direction: column;
    }

    main.content {
        padding: 18px;
    }
}
</style>