import React, { useState, useEffect, useCallback } from 'react';
import api from '../../api';
import Spinner from '../../components/Spinner';
import { Eye, Clock, CheckCircle, AlertTriangle, Trash2 } from 'lucide-react';

const StatusBadge = ({ status }) => {
    const statusMap = {
        pending: { text: 'Đang chờ', icon: <Clock size={14} />, color: 'amber' },
        completed: { text: 'Hoàn thành', icon: <CheckCircle size={14} />, color: 'emerald' },
        failed: { text: 'Thất bại', icon: <AlertTriangle size={14} />, color: 'red' },
    };
    const currentStatus = statusMap[status] || { text: status, color: 'slate' };
    
    return (
        <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-full bg-${currentStatus.color}-100 text-${currentStatus.color}-700`}>
            {currentStatus.icon}
            {currentStatus.text}
        </span>
    );
};

const AnalysisSessionManagementPage = () => {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchSessions = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.get('/admin/sessions');
            setSessions(response.data);
        } catch (error) {
            console.error("Lỗi khi lấy danh sách phiên phân tích:", error);
        } finally {
            setLoading(false);
        }
    }, []);
    
    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    const handleDeleteSession = async (sessionId) => {
        if (window.confirm('Bạn có chắc chắn muốn xóa phiên phân tích này?')) {
            try {
                await api.delete(`/admin/sessions/${sessionId}`);
                setSessions(currentSessions => currentSessions.filter(s => s.id !== sessionId));
                alert('Xóa phiên thành công!');
            } catch (error) {
                console.error('Lỗi khi xóa phiên:', error);
                alert('Xóa phiên thất bại.');
            }
        }
    };

    if (loading) return <Spinner />;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-slate-800">Quản lý Phiên phân tích</h1>
            </div>

            <div className="bg-white rounded-lg shadow-md border border-slate-200 overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
                        <tr>
                            <th className="p-4">ID Phiên</th>
                            <th className="p-4">Nông trại</th>
                            <th className="p-4">Thời gian tạo</th>
                            <th className="p-4">Chẩn đoán ban đầu</th>
                            <th className="p-4">Trạng thái</th>
                            <th className="p-4">Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sessions.map(session => (
                            <tr key={session.id} className="border-b border-slate-200 hover:bg-slate-50">
                                <td className="p-4 font-mono text-xs">{session.id.substring(0, 8)}...</td>
                                <td className="p-4 font-medium text-slate-800">{session.farm?.name || 'N/A'}</td>
                                <td className="p-4">{new Date(session.created_at).toLocaleString('vi-VN')}</td>
                                <td className="p-4">{session.initial_detection || 'Không có'}</td>
                                <td className="p-4"><StatusBadge status={session.status} /></td>
                                <td className="p-4 flex gap-2">
                                    <button className="text-gray-500 hover:text-gray-700" title="Xem chi tiết">
                                        <Eye size={18} />
                                    </button>
                                    <button 
                                        onClick={() => handleDeleteSession(session.id)}
                                        className="text-red-600 hover:text-red-800"
                                        title="Xóa"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default AnalysisSessionManagementPage;