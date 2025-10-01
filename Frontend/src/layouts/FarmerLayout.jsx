import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Microscope, History, Settings, LogOut, Bell, MessageCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

import FarmerDashboardPage from '../pages/farmer/FarmerDashboardPage';
import HistoryPage from '../pages/farmer/HistoryPage';
import SettingsPage from '../pages/farmer/SettingsPage'; 
import NotificationPage from '../pages/farmer/NotificationPage';
import QAPage from '../pages/farmer/QAPage';

const FarmerLayout = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login', { replace: true }); 
    };

    const navItems = [
        { to: "/farmer/dashboard", icon: <LayoutDashboard size={20} />, label: "Tổng Quan" },
        { to: "/farmer/notifications", icon: <Bell size={20} />, label: "Thông Báo" },
        { to: "/farmer/qa", icon: <MessageCircle size={20} />, label: "Hỏi Đáp AI" }, 
        { to: "/farmer/history", icon: <History size={20} />, label: "Lịch Sử" },
        { to: "/farmer/settings", icon: <Settings size={20} />, label: "Cài Đặt" },
    ];
    
    return (
        <div className="flex min-h-screen bg-slate-100">
            <aside className="w-64 bg-white p-4 flex flex-col border-r border-slate-200 shadow-sm fixed h-full">
                <div className="mb-10 p-2">
                    <h1 className="text-2xl font-bold text-emerald-600">AgriCare AI</h1>
                    <p className="text-sm text-slate-500">Xin chào, {user?.fullName || 'Nông dân'}</p>
                </div>
                <nav>
                    <ul className="space-y-2">
                        {navItems.map(item => (
                            <li key={item.to}>
                                <NavLink 
                                    to={item.to} 
                                    className={({isActive}) => `flex items-center gap-3 p-3 rounded-lg transition-colors text-base ${isActive ? 'bg-emerald-100 text-emerald-800 font-semibold' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
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
                    <Route path="dashboard" element={<FarmerDashboardPage />} />
                    <Route path="notifications" element={<NotificationPage />} />
                    <Route path="qa" element={<QAPage />} />
                    <Route path="history" element={<HistoryPage />} />
                    <Route path="settings" element={<SettingsPage />} />

                    <Route path="*" element={<Navigate to="/farmer/dashboard" replace />} />
                </Routes>
            </main>
        </div>
    );
};

export default FarmerLayout;