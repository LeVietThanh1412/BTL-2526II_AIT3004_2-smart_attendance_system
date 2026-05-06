<template>
    <div class="panel-card">
        <div class="activity-header">
            <h2>Hoạt động gần đây</h2>
            <router-link to="/admin/attendance-logs" class="view-all-link">Xem tất cả</router-link>
        </div>

        <div v-if="loading" class="loading">Đang tải dữ liệu...</div>

        <div v-else-if="errorMessage" class="loading error">{{ errorMessage }}</div>

        <ul v-else-if="activities.length" class="activity-list">
            <li v-for="(item, idx) in activities" :key="idx" class="activity-item">
                <div class="activity-user-info">
                    <div class="activity-user-details">
                        <h4>{{ item.name }}</h4>
                        <p>{{ item.time }} - {{ item.date }}</p>
                    </div>
                </div>
                <div class="result-status" :class="item.statusColor">
                    {{ item.status }}
                </div>
            </li>
        </ul>

        <div v-else class="loading">Chưa có hoạt động nào</div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchRecentActivities } from '../shared/api'

const loading = ref(true)
const activities = ref([])
const errorMessage = ref('')

const loadActivities = async () => {
    errorMessage.value = ''
    try {
        const data = await fetchRecentActivities()
        activities.value = data
    } catch (err) {
        console.error('[v0] Lỗi tải hoạt động:', err.message)
        activities.value = []
        errorMessage.value = 'Không thể tải hoạt động gần đây. Vui lòng thử lại.'
    } finally {
        loading.value = false
    }
}

onMounted(loadActivities)
</script>

<style scoped>
.activity-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.activity-header h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
}

.view-all-link {
    color: var(--primary-color);
    font-size: 11px;
    text-decoration: none;
    font-weight: 500;
}

.loading {
    padding: 20px;
    text-align: center;
    color: var(--text-sub);
    font-size: 13px;
}

.loading.error {
    color: var(--danger-color);
}

.activity-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.activity-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid var(--border-color);
}

.activity-user-details h4 {
    margin: 0;
    font-size: 12px;
    font-weight: 600;
}

.activity-user-details p {
    margin: 0;
    color: var(--text-sub);
    font-size: 10px;
}

.result-status {
    padding: 3px 8px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 600;
}

.result-status.green {
    background-color: #ecfdf5;
    color: var(--success-color);
}

.result-status.red {
    background-color: #fef2f2;
    color: var(--danger-color);
}

.result-status.yellow {
    background-color: #fffbeb;
    color: var(--warning-color);
}
</style>
