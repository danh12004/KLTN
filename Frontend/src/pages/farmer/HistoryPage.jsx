import React, { useState, useEffect } from 'react';
import { Clock, AlertCircle, ShieldCheck } from 'lucide-react';
import Spinner from '../../components/Spinner';
import api from '../../api'; 

const HistoryPage = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHistory = async () => {
            setLoading(true);
            try {
                const response = await api.get('/history');
                setHistory(response.data);
            } catch (error) {
                console.error("Failed to fetch history", error);
                setHistory([]); 
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

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Lịch Sử Phân Tích</h1>
            
            <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                {loading ? (
                    <Spinner />
                ) : (
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
                )}
            </div>
        </div>
    );
};

export default HistoryPage;