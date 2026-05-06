<template>
    <div class="panel-card stat-card" :class="color">
        <div class="stat-icon-wrapper">{{ icon }}</div>
        <div class="stat-info">
            <h3>{{ label }}</h3>
            <div class="stat-number">{{ value }}</div>
        </div>
    </div>
</template>

<script setup>
defineProps({
    color: { type: String, default: 'blue' },
    icon: { type: String, required: true },
    label: { type: String, required: true },
    value: { type: [String, Number], default: '--' },
})
</script>

<style scoped>
.stat-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 20px 10px;
}

.stat-icon-wrapper {
    margin-bottom: 12px;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}

.stat-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
}

.stat-info h3 {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    width: 100%;
    text-align: center;
    margin: 0 0 8px 0;
    color: var(--text-sub);
}

.stat-number {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 5px;
    color: var(--text-main);
    line-height: 1;
}

.stat-card.blue .stat-icon-wrapper {
    background-color: #f1f4ff;
    color: var(--primary-color);
}

.stat-card.green .stat-icon-wrapper {
    background-color: #ecfdf5;
    color: var(--success-color);
}

.stat-card.yellow .stat-icon-wrapper {
    background-color: #fffbeb;
    color: var(--warning-color);
}

.stat-card.red .stat-icon-wrapper {
    background-color: #fef2f2;
    color: var(--danger-color);
}
</style>
