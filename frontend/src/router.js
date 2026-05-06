// =====================================================================
// router.js - Cấu hình đường dẫn (Vue Router)
// Hệ thống chỉ còn 2 chức năng chính:
//   1) Báo cáo thống kê (Dashboard) - dành cho Admin
//   2) Đăng ký điểm danh (quay video khuôn mặt)
// Cộng thêm trang điểm danh hằng ngày cho User (chụp ảnh)
// =====================================================================
import { createRouter, createWebHistory } from 'vue-router'

const Dashboard = () => import('./admin/pages/Dashboard.vue')
const RegisterAttendance = () => import('./admin/pages/RegisterAttendance.vue')
const CheckIn = () => import('./user/CheckIn.vue')

const routes = [
    { path: '/', redirect: '/admin/dashboard' },

    // Trang Admin
    { path: '/admin/dashboard', name: 'Dashboard', component: Dashboard },
    { path: '/admin/register', name: 'RegisterAttendance', component: RegisterAttendance },

    // Trang User: chụp ảnh để điểm danh hằng ngày
    { path: '/checkin', name: 'CheckIn', component: CheckIn },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
