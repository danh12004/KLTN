import React, { useState, useEffect } from 'react';
import { Clock, AlertCircle, ShieldCheck } from 'lucide-react';
import Spinner from '../../components/Spinner';
import api from '../../api'; 

const HistoryPage = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                setLoading(true);
                const response = await api.get('/user/history');
                setHistory(response.data);
            } catch (err) {
                console.error("Failed to fetch history", err);
                setError("Không thể tải lịch sử. Vui lòng thử lại.");
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    const getStatusChip = (status) => {
        switch (status) {
            case 'Đã xử lý':
                return 'bg-blue-100 text-blue-800';
            case 'An toàn':
                return 'bg-green-100 text-green-800';
            case 'Cảnh báo':
                return 'bg-yellow-100 text-yellow-800';
            default:
                return 'bg-slate-100 text-slate-800';
        }
    };

    const renderContent = () => {
        if (loading) return <div className="flex justify-center p-8"><Spinner /></div>;
        if (error) {
            return (
                <div className="text-center p-8 text-red-700 bg-red-50 rounded-lg">
                    <Frown className="mx-auto mb-2" /> {error}
                </div>
            );
        }
        if (history.length === 0) {
            return (
                <div className="text-center p-8 text-slate-500">
                    <History className="mx-auto mb-2" />
                    Chưa có hoạt động nào được ghi lại.
                </div>
            );
        }
        return (
            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="border-b-2 border-slate-200">
                        <tr>
                            <th className="p-4 text-sm font-semibold text-slate-600">Ngày</th>
                            <th className="p-4 text-sm font-semibold text-slate-600">Kết quả chẩn đoán</th>
                            <th className="p-4 text-sm font-semibold text-slate-600">Mức độ rủi ro</th>
                            <th className="p-4 text-sm font-semibold text-slate-600">Trạng thái</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history.map((item) => (
                            <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="p-4 text-slate-700">{item.date}</td>
                                <td className="p-4 font-medium text-slate-800">{item.disease}</td>
                                <td className="p-4 text-slate-700">{item.risk}</td>
                                <td className="p-4">
                                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusChip(item.status)}`}>
                                        {item.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Lịch Sử Phân Tích</h1>
            <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                {renderContent()}
            </div>
        </div>
    );
};

export default HistoryPage;