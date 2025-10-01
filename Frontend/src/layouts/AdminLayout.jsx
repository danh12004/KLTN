// src/layouts/AdminLayout.jsx

import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Wheat, LogOut, Microscope } from 'lucide-react'; 
import { useAuth } from '../context/AuthContext';

import UserManagementPage from '../pages/admin/UserManagementPage';
import FarmManagementPage from '../pages/admin/FarmManagementPage';
import AnalysisSessionManagementPage from '../pages/admin/AnalysisSessionManagementPage';
import AdminDashboardPage from '../pages/admin/AdminDashboardPage'; 

const AdminLayout = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login', { replace: true }); 
    };
    
    const navItems = [
        { to: "/admin/dashboard", icon: <LayoutDashboard size={20} />, label: "Thống Kê" },
        { to: "/admin/users", icon: <Users size={20} />, label: "Quản lý Nông dân" },
        { to: "/admin/farms", icon: <Wheat size={20} />, label: "Quản lý Nông trại" },
        { to: "/admin/sessions", icon: <Microscope size={20} />, label: "Quản lý Phân tích" },
    ];

    return (
        <div className="flex min-h-screen bg-slate-100">
            <aside className="w-64 bg-white p-4 flex flex-col border-r border-slate-200 shadow-sm fixed h-full">
                <div className="mb-10 p-2">
                    <h1 className="text-2xl font-bold text-blue-600">Admin Panel</h1>
                    <p className="text-sm text-slate-500">Xin chào, {user?.fullName || 'Quản trị viên'}</p>
                </div>
                <nav>
                    <ul className="space-y-2">
                        {navItems.map(item => (
                            <li key={item.to}>
                                <NavLink 
                                    to={item.to} 
                                    className={({isActive}) => `flex items-center gap-3 p-3 rounded-lg transition-colors text-base ${isActive ? 'bg-blue-100 text-blue-700 font-semibold' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
                                >
                                    {item.icon}<span>{item.label}</span>
                                </NavLink>
                            </li>
                        ))}
                    </ul>
                </nav>
                <div className="mt-auto">
                    <button onClick={handleLogout} className="flex items-center gap-3 w-full p-3 rounded-lg text-slate-600 hover:bg-red-50 hover:text-red-600 transition-colors">
                        <LogOut size={20} /><span>Đăng xuất</span>
                    </button>
                </div>
            </aside>
            
            <main className="flex-1 p-6 lg:p-8 ml-64">
                <Routes>
                    <Route path="dashboard" element={<AdminDashboardPage />} />
                    <Route path="users" element={<UserManagementPage />} />
                    <Route path="farms" element={<FarmManagementPage />} />
                    <Route path="sessions" element={<AnalysisSessionManagementPage />} />
                    <Route index element={<Navigate to="dashboard" />} /> 
                </Routes>
            </main>
        </div>
    );
};

export default AdminLayout;