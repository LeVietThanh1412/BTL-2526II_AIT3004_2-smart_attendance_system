<template>
    <aside class="sidebar">
        <div>
            <div class="logo-area">
                <div class="logo-icon">SA</div>
                <div>
                    <h2 style="margin:0; font-size:16px;">Smart Attendance</h2>
                    <p style="margin:0; color:var(--text-sub); font-size:10px;">AI Face Recognition</p>
                </div>
            </div>

            <nav class="nav-area">
                <h3>Tổng quan</h3>
                <ul>
                    <li>
                        <router-link to="/admin/dashboard" active-class="active">
                            <span>📊</span> Báo cáo thống kê
                        </router-link>
                    </li>
                </ul>

                <h3>Chức năng</h3>
                <ul>
                    <li>
                        <router-link to="/admin/register" active-class="active">
                            <span>🎥</span> Đăng ký điểm danh
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/checkin" active-class="active">
                            <span>📷</span> Camera điểm danh
                        </router-link>
                    </li>
                </ul>

                <h3>Hệ thống</h3>
                <ul>
                    <li><a href="#"><span>⚙️</span> Cài đặt</a></li>
                    <li><a href="#"><span>❓</span> Trợ giúp</a></li>
                </ul>
            </nav>
        </div>
    </aside>
</template>

<script setup>
// Sidebar dùng chung cho mọi trang Admin
</script>

<style scoped>
aside.sidebar {
    width: 220px;
    background-color: var(--card-color);
    padding: 25px 20px;
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex-shrink: 0;
}

.logo-area {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 35px;
}

.logo-icon {
    width: 36px;
    height: 36px;
    background-color: var(--primary-color);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 18px;
}

.nav-area {
    flex-grow: 1;
    overflow-y: auto;
    padding-right: 5px;
}

.nav-area h3 {
    text-transform: uppercase;
    color: var(--text-sub);
    font-size: 11px;
    margin-top: 25px;
    margin-bottom: 8px;
    padding-left: 15px;
    letter-spacing: 1px;
}

.nav-area ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.nav-area li {
    margin-bottom: 3px;
}

.nav-area a {
    text-decoration: none;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 15px;
    border-radius: 8px;
    font-weight: 500;
    font-size: 14px;
    transition: background-color 0.2s;
}

.nav-area a:hover,
.nav-area a.active {
    background-color: #f1f4ff;
    color: var(--primary-color);
}
</style>
