<template>
    <div class="app-container">
        <AdminSidebar />

        <main class="content">
            <TopHeader title="Tổng quan hệ thống" />

            <div class="dashboard-grid">
                <div class="right-main-column">
                    <div class="stacked-stats-grid">
                        <StatCard color="blue" icon="👥" label="Tổng nhân viên" :value="stats.total ?? '--'" />
                        <StatCard color="yellow" icon="⏳" label="Chưa điểm danh" :value="stats.missing ?? '--'" />
                        <StatCard color="green" icon="✓" label="Đúng giờ" :value="stats.onTime ?? '--'" />
                        <StatCard color="red" icon="✗" label="Đi muộn" :value="stats.late ?? '--'" />
                    </div>
                    <p v-if="statsError" class="error-text">{{ statsError }}</p>

                    <RecentActivity />

                    <div class="panel-card today-stats">
                        <h2>Thống kê hôm nay</h2>
                        <div class="today-summary" v-if="statsLoaded">
                            <span>Đã điểm danh</span>
                            <strong>{{ checkedInCount }} / {{ stats.total }}</strong>
                        </div>
                        <div class="today-summary error" v-else>
                            Chưa có dữ liệu thống kê.
                        </div>
                        <div class="chart-container">
                            <canvas ref="chartEl"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue'
import Chart from 'chart.js/auto'

import AdminSidebar from './AdminSidebar.vue'
import TopHeader from './TopHeader.vue'
import StatCard from './StatCard.vue'
import RecentActivity from './RecentActivity.vue'

import { fetchStatistics } from '../shared/api'

const chartEl = ref(null)

const statsError = ref('')
const statsLoaded = ref(false)
const stats = reactive({ total: null, missing: null, onTime: null, late: null })

const checkedInCount = computed(() => {
    if (!statsLoaded.value) return null
    const totalValue = Number(stats.total ?? 0)
    const missingValue = Number(stats.missing ?? 0)
    return Math.max(0, totalValue - missingValue)
})

let chartInstance = null

// === Tải số liệu thống kê & vẽ biểu đồ ===
const loadStatistics = async () => {
    statsError.value = ''
    try {
        const data = await fetchStatistics()
        Object.assign(stats, data)
        statsLoaded.value = true
    } catch (err) {
        console.error('[v0] Lỗi tải thống kê:', err.message)
        Object.assign(stats, { total: null, missing: null, onTime: null, late: null })
        statsLoaded.value = false
        statsError.value = 'Không thể tải thống kê từ hệ thống. Vui lòng thử lại.'
    }
    drawChart()
}

const drawChart = () => {
    if (!chartEl.value) return
    if (chartInstance) {
        chartInstance.destroy()
        chartInstance = null
    }
    if (!statsLoaded.value) return

    const checkedInValue = Number(checkedInCount.value ?? 0)
    const missingValue = Number(stats.missing ?? 0)

    chartInstance = new Chart(chartEl.value.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Đã điểm danh', 'Chưa điểm danh'],
            datasets: [{
                data: [checkedInValue, missingValue],
                backgroundColor: ['#10b981', '#f59e0b'],
                borderWidth: 0,
                hoverOffset: 10,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 20, font: { size: 12 } } },
            },
            cutout: '70%',
        },
    })
}

watch(() => ({ ...stats, loaded: statsLoaded.value }), drawChart, { deep: true })

onMounted(() => {
    loadStatistics()
})

onUnmounted(() => {
    if (chartInstance) chartInstance.destroy()
})
</script>

<style scoped>
.app-container {
    display: flex;
    width: 100%;
    height: 100vh;
    overflow: hidden;
}

main.content {
    flex-grow: 1;
    padding: 25px 30px;
    overflow-y: auto;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
    align-items: start;
}

.right-main-column {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
}


.stacked-stats-grid {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
}

@media (max-width: 1100px) {
    .right-main-column {
        grid-template-columns: 1fr;
    }

    .stacked-stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 720px) {
    .stacked-stats-grid {
        grid-template-columns: 1fr;
    }
}

.error-text {
    margin: -6px 0 10px;
    color: var(--danger-color);
    font-size: 12px;
}

.chart-container {
    position: relative;
    height: 250px;
    width: 100%;
}

.today-summary {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    font-size: 13px;
    color: var(--text-sub);
    margin-bottom: 10px;
}

.today-summary strong {
    font-size: 16px;
    color: var(--text-main);
}

.today-summary.error {
    color: var(--danger-color);
}
</style>
