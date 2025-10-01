import React, { useState, useEffect } from 'react';
import api from '../../api';
import Spinner from '../../components/Spinner';
import { Users, Wheat, Microscope } from 'lucide-react';

const StatCard = ({ icon, title, value, colorClass }) => (
    <div className="bg-white p-6 rounded-lg shadow-md border border-slate-200 flex items-center gap-4">
        <div className={`p-3 rounded-full ${colorClass}`}>
            {icon}
        </div>
        <div>
            <p className="text-sm text-slate-500 font-medium">{title}</p>
            <p className="text-2xl font-bold text-slate-800">{value}</p>
        </div>
    </div>
);

const AdminDashboardPage = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await api.get('/admin/stats'); 
                setStats(response.data);
            } catch (error) {
                console.error("Lỗi khi lấy dữ liệu thống kê:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);

    if (loading) return <Spinner />;
    
    if (!stats) return <p>Không thể tải dữ liệu thống kê.</p>;

    return (
        <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Thống kê chung</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <StatCard 
                    icon={<Users size={24} className="text-blue-600" />}
                    title="Tổng số Người dùng"
                    value={stats.totalUsers}
                    colorClass="bg-blue-100"
                />
                <StatCard 
                    icon={<Wheat size={24} className="text-emerald-600" />}
                    title="Tổng số Nông trại"
                    value={stats.totalFarms}
                    colorClass="bg-emerald-100"
                />
                <StatCard 
                    icon={<Microscope size={24} className="text-amber-600" />}
                    title="Tổng số Lượt phân tích"
                    value={stats.totalSessions}
                    colorClass="bg-amber-100"
                />
            </div>
        </div>
    );
};

export default AdminDashboardPage;