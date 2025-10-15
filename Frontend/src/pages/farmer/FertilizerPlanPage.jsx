import React, { useState } from 'react';
import { Leaf, FlaskConical, Tractor, Frown } from 'lucide-react';
import api from '../../api';

const Spinner = ({ size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-6 h-6',
        md: 'w-10 h-10',
    };
    return (
        <div className={`animate-spin rounded-full border-4 border-t-4 border-slate-200 border-t-emerald-600 ${sizeClasses[size]}`}></div>
    );
};

const FertilizerPlanPage = () => {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const generatePlan = async () => {
        setLoading(true);
        setError('');
        setPlan(null);
        try {
            const response = await api.get('/farm/fertilizer-plan');
            setPlan(response.data);
        } catch (err) {
            setError('Không thể tạo kế hoạch bón phân lúc này. Vui lòng thử lại sau.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Kế Hoạch Bón Phân</h1>
            <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center">
                <Leaf size={48} className="mx-auto text-emerald-500 mb-4" />
                <h2 className="text-xl font-bold text-slate-700">Tối ưu hóa dinh dưỡng cho cây lúa</h2>
                <p className="text-slate-500 mt-2 mb-6 max-w-xl mx-auto">
                    Nhận một kế hoạch bón phân chi tiết, phù hợp với giai đoạn sinh trưởng của cây trồng và điều kiện đất đai của bạn.
                </p>
                <button
                    onClick={generatePlan}
                    disabled={loading}
                    className="bg-emerald-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-slate-400 flex items-center justify-center mx-auto cursor-pointer"
                >
                    {loading ? <Spinner size="sm" /> : 'Tạo Kế hoạch Ngay'}
                </button>
            </div>

            {error && (
                <div className="mt-8 text-center p-6 bg-red-50 text-red-700 rounded-lg shadow-md border border-red-200">
                    <Frown className="mx-auto mb-2" /> {error}
                </div>
            )}

            {plan && plan.fertilization_stages && Array.isArray(plan.fertilization_stages) && (
                <div className="mt-8 animate-fade-in">
                    <h2 className="text-2xl font-bold text-slate-800 mb-4">{plan.main_summary || 'Kế hoạch đề xuất:'}</h2>
                    <div className="space-y-6">
                        {plan.fertilization_stages.map((stage, index) => (
                            <div key={index} className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                                <h3 className="text-lg font-bold text-emerald-700 mb-1">{stage.stage_name}</h3>
                                <p className="text-sm text-slate-500 mb-4">Thời điểm: {stage.timing}</p>
                                
                                <div className="space-y-4">
                                    {stage.fertilizers.map((fertilizer, fertIndex) => (
                                        <div key={fertIndex} className="p-4 bg-slate-50 rounded-lg">
                                            <p className="font-bold text-slate-800 mb-2">{fertilizer.type}</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                                <InfoItem 
                                                    icon={<Tractor size={20} />} 
                                                    label="Liều lượng" 
                                                    value={`${fertilizer.quantity_kg} kg`} 
                                                />
                                                <InfoItem 
                                                    icon={<Leaf size={20} />} 
                                                    label="Hướng dẫn" 
                                                    value={fertilizer.instructions} 
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                        {plan.additional_advice && (
                            <div className="mt-6 bg-blue-50 p-4 rounded-lg border border-blue-200 text-blue-800">
                                <h4 className="font-bold mb-2">Tư vấn bổ sung</h4>
                                <p className="text-sm">{plan.additional_advice}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

const InfoItem = ({ icon, label, value }) => (
    <div className="flex items-start gap-3">
        <div className="text-emerald-600 mt-1">{icon}</div>
        <div>
            <p className="font-semibold text-slate-600">{label}</p>
            <p className="text-slate-800">{value}</p>
        </div>
    </div>
);

export default FertilizerPlanPage;
