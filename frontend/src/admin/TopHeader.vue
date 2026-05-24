<template>
    <header class="top-header">
        <h1>{{ title }}</h1>
        <div class="header-actions">
            <router-link to="/checkin" class="back-checkin-btn">
                <span>📷</span> Điểm danh
            </router-link>

            <div class="date-time">
                <span><span>📅</span> {{ currentDate }}</span>
                <span><span>⏱️</span> {{ currentTime }}</span>
            </div>

            <button class="notification-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                <span v-if="notificationCount > 0" class="notification-badge">
                    {{ notificationCount }}
                </span>
            </button>
        </div>
    </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { formatDate, formatTime } from '../shared/dateUtils'
import { fetchNotificationCount } from '../shared/api'

defineProps({
    title: {
        type: String,
        default: 'Tổng quan hệ thống',
    },
})

const currentDate = ref(formatDate())
const currentTime = ref(formatTime())
const notificationCount = ref(0)

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
    } catch (err) {
        console.error('[v0] Lỗi tải thông báo:', err.message)
        notificationCount.value = 0
    }
}

onMounted(() => {
    updateDateTime()
    timerId = setInterval(updateDateTime, 1000)
    loadNotifications()
})

onUnmounted(() => {
    if (timerId) clearInterval(timerId)
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

.back-checkin-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background-color: var(--primary-color, #3b82f6);
    color: white;
    text-decoration: none;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 15px;
    border-radius: 8px;
    transition: opacity 0.2s;
}

.back-checkin-btn:hover {
    opacity: 0.9;
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
}

.notification-badge {
    position: absolute;
    top: -4px;
    right: -4px;
    width: 16px;
    height: 16px;
    background-color: var(--danger-color);
    color: white;
    font-size: 10px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}
</style>
