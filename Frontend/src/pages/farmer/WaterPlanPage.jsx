import React, { useState } from 'react';
import { Droplet, Sun, Wind, Frown } from 'lucide-react';
import api from '../../api';

const Spinner = ({ size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-6 h-6',
        md: 'w-10 h-10',
    };
    return (
        <div className={`animate-spin rounded-full border-4 border-t-4 border-slate-200 border-t-blue-600 ${sizeClasses[size]}`}></div>
    );
};

const WaterPlanPage = () => {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const generatePlan = async () => {
        setLoading(true);
        setError('');
        setPlan(null);
        try {
            const response = await api.get('/farm/water-plan');
            setPlan(response.data);
        } catch (err) {
            setError(err.response?.data?.error || 'Không thể tạo kế hoạch tưới tiêu. Vui lòng thử lại.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Kế Hoạch Quản Lý Nước</h1>
            <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center">
                <Droplet size={48} className="mx-auto text-blue-500 mb-4" />
                <h2 className="text-xl font-bold text-slate-700">Quản lý nước tưới thông minh</h2>
                <p className="text-slate-500 mt-2 mb-6 max-w-xl mx-auto">
                    Dựa trên dữ liệu cảm biến IoT và thời tiết, hệ thống sẽ đề xuất kế hoạch tưới tiêu tối ưu để tiết kiệm nước và đảm bảo cây lúa phát triển tốt nhất.
                </p>
                <button
                    onClick={generatePlan}
                    disabled={loading}
                    className="bg-blue-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-slate-400 flex items-center justify-center mx-auto cursor-pointer"
                >
                    {loading ? <Spinner size="sm" /> : 'Lấy Kế hoạch Tưới tiêu'}
                </button>
            </div>
            
            {error && (
                <div className="mt-8 text-center p-6 bg-red-50 text-red-700 rounded-lg shadow-md border border-red-200">
                    <Frown className="mx-auto mb-2" /> {error}
                </div>
            )}

            {plan && (
                <div className="mt-8 animate-fade-in bg-white p-8 rounded-xl shadow-md border border-slate-200">
                    <h2 className="text-2xl font-bold text-slate-800 mb-2 text-center">Đề xuất Quản lý nước</h2>
                    
                    <p className="text-center text-blue-600 font-bold mb-4 text-2xl uppercase">
                        {plan.main_recommendation || 'Không có đề xuất'}
                    </p>

                    <p className="text-center text-slate-600 mb-8 max-w-2xl mx-auto">
                        <strong>Lý do:</strong> {plan.reason || 'Chưa có giải thích chi tiết.'}
                    </p>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                        <DayPlanCard day="Hôm nay" planText={plan.three_day_plan?.today} />
                        <DayPlanCard day="Ngày mai" planText={plan.three_day_plan?.tomorrow} />
                        <DayPlanCard day="Ngày kia" planText={plan.three_day_plan?.day_after_tomorrow} />
                    </div>

                    {plan.current_assessment &&
                        <div className="mt-8 text-center p-4 bg-slate-50 text-slate-700 rounded-lg border border-slate-200">
                            <h4 className="font-semibold">Đánh giá tình hình hiện tại</h4>
                            <p className="text-sm">{plan.current_assessment}</p>
                        </div>
                    }
                </div>
            )}
        </div>
    );
};

const DayPlanCard = ({ day, planText }) => (
    <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
        <h3 className="font-bold text-slate-800 text-md mb-2">{day}</h3>
        <p className="text-sm text-slate-600">{planText || 'Chưa có kế hoạch.'}</p>
    </div>
);

export default WaterPlanPage;

