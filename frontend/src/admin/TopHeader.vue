<template>
    <header class="top-header">
        <h1>{{ title }}</h1>
        <div class="header-actions">
            <div class="date-time">
                <span><span>📅</span> {{ currentDate }}</span>
                <span><span>⏱️</span> {{ currentTime }}</span>
            </div>

            <div class="notification-container" ref="notificationContainer">
                <button class="notification-btn" @click="toggleDropdown" aria-label="Notifications">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <span v-if="displayCount > 0" class="notification-badge">
                        {{ displayCount }}
                    </span>
                </button>

                <!-- Dropdown Menu -->
                <transition name="fade-slide">
                    <div v-if="showDropdown" class="notification-dropdown">
                        <!-- Trạng thái Admin đã đăng nhập -->
                        <div v-if="isAdmin" class="admin-notifications">
                            <div class="dropdown-header">
                                <h3>Thông báo hệ thống</h3>
                                <button v-if="notifications.length > 0" class="mark-read-btn" @click="markAllAsRead">
                                    Đọc tất cả
                                </button>
                            </div>

                            <div class="dropdown-body custom-scrollbar">
                                <div v-if="loading" class="loading-state">
                                    <div class="spinner"></div>
                                    <p>Đang tải thông báo...</p>
                                </div>
                                <div v-else-if="notifications.length === 0" class="empty-state">
                                    <span class="empty-icon">🎉</span>
                                    <p>Hôm nay hệ thống không có cảnh báo nào cần duyệt hoặc kiểm tra.</p>
                                </div>
                                <div v-else class="notification-list">
                                    <div 
                                        v-for="item in notifications" 
                                        :key="item.id" 
                                        class="notification-item" 
                                        :class="item.type"
                                        @click="handleNotificationClick(item)"
                                    >
                                        <div class="notification-icon-wrapper">
                                            <span v-if="item.type === 'attendance_failed'">❌</span>
                                            <span v-else-if="item.type === 'attendance_late'">⚠️</span>
                                            <span v-else-if="item.type === 'new_student'">👤</span>
                                            <span v-else-if="item.type === 'schedule_change'">📅</span>
                                        </div>
                                        <div class="notification-info">
                                            <h4 class="notification-title">{{ item.title }}</h4>
                                            <p class="notification-desc">{{ item.message }}</p>
                                            <span class="notification-meta">{{ item.date }} lúc {{ item.time }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="dropdown-footer">
                                <router-link to="/admin/attendance-logs" class="view-all-btn" @click="showDropdown = false">
                                    Lịch sử điểm danh →
                                </router-link>
                            </div>
                        </div>

                        <!-- Trạng thái chưa đăng nhập (Sinh viên / Khách vãng lai) -->
                        <div v-else class="guest-notifications">
                            <div class="dropdown-header">
                                <h3>Hỗ trợ điểm danh</h3>
                            </div>
                            <div class="dropdown-body custom-scrollbar">
                                <div class="login-prompt">
                                    <p>Tính năng xem lịch sử cảnh báo điểm danh, duyệt danh sách thành viên và đăng ký ca học chỉ dành cho Quản trị viên.</p>
                                    <button class="login-btn" @click="goToLogin">Đăng nhập Admin</button>
                                </div>
                                <div class="student-guide-section">
                                    <h4 class="guide-title">📢 Hướng dẫn điểm danh đúng cách</h4>
                                    <ul class="guide-steps">
                                        <li><span class="step-num">1</span> Đứng trước camera khoảng 0.5m - 1.5m.</li>
                                        <li><span class="step-num">2</span> Nhập chính xác Mã sinh viên (VD: SV001).</li>
                                        <li><span class="step-num">3</span> Nhấn "Bắt đầu điểm danh", giữ đầu thẳng và nhìn vào camera.</li>
                                    </ul>
                                    <h4 class="guide-title mt-15">⏰ Quy định ca học</h4>
                                    <div class="guide-time-rule">
                                        Giờ học chính thức tính điểm danh từ <strong>07:30</strong> sáng. Hệ thống sẽ ghi nhận trạng thái <strong>Vào muộn</strong> nếu check-in sau thời gian này.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </transition>
            </div>
        </div>
    </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { formatDate, formatTime } from '../shared/dateUtils'
import { fetchNotificationCount, fetchNotificationList } from '../shared/api'

defineProps({
    title: {
        type: String,
        default: 'Tổng quan hệ thống',
    },
})

// Router
const router = useRouter()

const currentDate = ref(formatDate())
const currentTime = ref(formatTime())
const notificationCount = ref(0)
const displayCount = ref(0)
const showDropdown = ref(false)
const notifications = ref([])
const loading = ref(false)
const lastReadTime = ref(localStorage.getItem('lastReadNotificationTime') || '')

const isAdmin = computed(() => {
    return !!localStorage.getItem('adminToken')
})

let timerId = null

const updateDateTime = () => {
    const now = new Date()
    currentDate.value = formatDate(now)
    currentTime.value = formatTime(now)
}

const loadNotifications = async () => {
    try {
        const data = await fetchNotificationCount()
        notificationCount.value = Number(data?.count ?? 0)
        
        // Tải danh sách nếu là admin để tính chính xác displayCount
        if (isAdmin.value) {
            const list = await fetchNotificationList()
            notifications.value = list
            
            // Tính số lượng hiển thị chưa đọc dựa trên lastReadTime
            if (lastReadTime.value) {
                const readLimit = new Date(lastReadTime.value)
                let unread = 0
                for (const item of list) {
                    try {
                        const [d, m, y] = item.date.split('/')
                        const parsedDate = new Date(`${y}-${m}-${d}T${item.time}`)
                        if (parsedDate > readLimit) {
                            unread++
                        }
                    } catch (e) {
                        unread++
                    }
                }
                displayCount.value = unread
            } else {
                displayCount.value = notificationCount.value
            }
        } else {
            displayCount.value = 0
        }
    } catch (err) {
        console.error('[v0] Lỗi tải thông báo:', err.message)
        notificationCount.value = 0
        displayCount.value = 0
    }
}

const toggleDropdown = async () => {
    showDropdown.value = !showDropdown.value
    if (showDropdown.value && isAdmin.value) {
        loading.value = true
        try {
            const list = await fetchNotificationList()
            notifications.value = list
        } catch (err) {
            console.error('Lỗi tải danh sách thông báo:', err)
        } finally {
            loading.value = false
        }
    }
}

const closeDropdown = () => {
    showDropdown.value = false
}

// Đánh dấu toàn bộ đã đọc
const markAllAsRead = () => {
    const nowStr = new Date().toISOString()
    localStorage.setItem('lastReadNotificationTime', nowStr)
    lastReadTime.value = nowStr
    displayCount.value = 0
}

// Chuyển hướng khi admin click thông báo
const handleNotificationClick = (item) => {
    showDropdown.value = false
    if (item.route) {
        router.push(item.route)
    }
}

// Chuyển hướng tới login
const goToLogin = () => {
    showDropdown.value = false
    router.push('/login')
}

// Click outside handling
const notificationContainer = ref(null)
const handleClickOutside = (event) => {
    if (notificationContainer.value && !notificationContainer.value.contains(event.target)) {
        closeDropdown()
    }
}

onMounted(() => {
    updateDateTime()
    timerId = setInterval(updateDateTime, 1000)
    loadNotifications()
    
    // Tự động tải lại thông báo mỗi 30 giây để cập nhật thời gian thực
    const notificationTimer = setInterval(loadNotifications, 30000)
    
    document.addEventListener('click', handleClickOutside)
    
    onUnmounted(() => {
        clearInterval(notificationTimer)
    })
})

onUnmounted(() => {
    if (timerId) clearInterval(timerId)
    document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
header.top-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 25px;
}

header h1 {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 15px;
}

.date-time {
    display: flex;
    gap: 15px;
    color: var(--text-sub);
    font-size: 13px;
    background-color: var(--card-color);
    padding: 8px 15px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
}

.date-time span {
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ========================================================
   CSS CHO NÚT THÔNG BÁO & DROPDOWN POPUP
   ======================================================== */
.notification-container {
    position: relative;
    display: inline-block;
}

.notification-btn {
    position: relative;
    background: var(--card-color);
    border: 1px solid var(--border-color);
    cursor: pointer;
    padding: 8px;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.notification-btn:hover {
    background-color: #f1f5f9;
    transform: scale(1.05);
}

.notification-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    width: 16px;
    height: 16px;
    background-color: var(--danger-color, #ef4444);
    color: white;
    font-size: 10px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    box-shadow: 0 0 0 2px var(--card-color);
}

/* Dropdown Menu Glassmorphism */
.notification-dropdown {
    position: absolute;
    top: 45px;
    right: 0;
    width: 380px;
    max-height: 480px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(226, 232, 240, 0.8);
    border-radius: 16px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
    z-index: 999;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.dropdown-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 20px;
    border-bottom: 1px solid var(--border-color);
}

.dropdown-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
}

.mark-read-btn {
    background: none;
    border: none;
    color: var(--primary-color, #3b82f6);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.mark-read-btn:hover {
    background-color: rgba(59, 130, 246, 0.1);
}

.dropdown-body {
    flex-grow: 1;
    overflow-y: auto;
    max-height: 350px;
}

.dropdown-footer {
    padding: 12px;
    text-align: center;
    border-top: 1px solid var(--border-color);
    background-color: #f8fafc;
}

.view-all-btn {
    font-size: 12px;
    font-weight: 600;
    color: var(--primary-color, #3b82f6);
    text-decoration: none;
    transition: opacity 0.2s;
}

.view-all-btn:hover {
    opacity: 0.8;
}

/* Notification List & Items */
.notification-list {
    display: flex;
    flex-direction: column;
}

.notification-item {
    display: flex;
    gap: 12px;
    padding: 12px 18px;
    border-bottom: 1px solid #f1f5f9;
    cursor: pointer;
    transition: background-color 0.2s;
}

.notification-item:hover {
    background-color: #f8fafc;
}

.notification-item:last-child {
    border-bottom: none;
}

.notification-icon-wrapper {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 14px;
}

.attendance_failed .notification-icon-wrapper {
    background-color: #fef2f2;
}

.attendance_late .notification-icon-wrapper {
    background-color: #fffbeb;
}

.new_student .notification-icon-wrapper {
    background-color: #eff6ff;
}

.schedule_change .notification-icon-wrapper {
    background-color: #f0fdf4;
}

.notification-info {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.notification-title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
}

.notification-desc {
    margin: 0;
    font-size: 12px;
    color: #475569;
    line-height: 1.4;
}

.notification-meta {
    font-size: 10px;
    color: #94a3b8;
}

/* Loading & Empty States */
.loading-state, .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
    color: #64748b;
    gap: 12px;
}

.empty-icon {
    font-size: 32px;
}

.loading-state p, .empty-state p {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
}

.spinner {
    width: 24px;
    height: 24px;
    border: 3px solid #e2e8f0;
    border-top: 3px solid var(--primary-color, #3b82f6);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

/* Guest Mode Styles */
.login-prompt {
    padding: 20px;
    background-color: #f8fafc;
    border-bottom: 1px solid var(--border-color);
    text-align: center;
}

.login-prompt p {
    margin: 0 0 12px;
    font-size: 12px;
    color: #475569;
    line-height: 1.5;
}

.login-btn {
    width: 100%;
    background-color: var(--primary-color, #3b82f6);
    color: white;
    border: none;
    padding: 10px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
}

.login-btn:hover {
    opacity: 0.9;
}

.student-guide-section {
    padding: 20px;
}

.guide-title {
    margin: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
}

.mt-15 {
    margin-top: 15px;
}

.guide-steps {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.guide-steps li {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: #475569;
    line-height: 1.4;
}

.step-num {
    background-color: #f1f5f9;
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
}

.guide-time-rule {
    font-size: 12px;
    color: #475569;
    line-height: 1.5;
    background-color: #fffbeb;
    border: 1px solid #fde68a;
    padding: 10px;
    border-radius: 8px;
}

/* Custom Scrollbar */
.custom-scrollbar::-webkit-scrollbar {
    width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* Transition Animations */
.fade-slide-enter-active, .fade-slide-leave-active {
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from, .fade-slide-leave-to {
    opacity: 0;
    transform: translateY(-10px) scale(0.98);
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
