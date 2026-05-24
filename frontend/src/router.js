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
const AttendanceLogs = () => import('./admin/pages/AttendanceLogs.vue')
const Login = () => import('./admin/pages/Login.vue')
const ManageMembers = () => import('./admin/pages/ManageMembers.vue')
const CheckIn = () => import('./user/CheckIn.vue')

const routes = [
    { path: '/', redirect: '/checkin' },

    // Trang Admin
    { path: '/login', name: 'Login', component: Login },
    { path: '/admin/dashboard', name: 'Dashboard', component: Dashboard, meta: { requiresAuth: true } },
    { path: '/admin/register', name: 'RegisterAttendance', component: RegisterAttendance },
    { path: '/admin/attendance-logs', name: 'AttendanceLogs', component: AttendanceLogs, meta: { requiresAuth: true } },
    { path: '/admin/members', name: 'ManageMembers', component: ManageMembers, meta: { requiresAuth: true } },

    // Trang User: chụp ảnh để điểm danh hằng ngày
    { path: '/checkin', name: 'CheckIn', component: CheckIn },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('adminToken')
    
    // Nếu vào route bắt buộc đăng nhập mà chưa có token
    if (to.meta.requiresAuth && !token) {
        next({ name: 'Login' })
    } 
    // Nếu đã đăng nhập mà vào lại trang login thì chuyển về dashboard
    else if (to.name === 'Login' && token) {
        next({ name: 'Dashboard' })
    } 
    else {
        next()
    }
})

export default router
