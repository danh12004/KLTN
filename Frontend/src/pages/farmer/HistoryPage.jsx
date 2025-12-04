import React, { useState, useEffect } from 'react';
import { Frown, History, X, Droplet, Leaf, Zap, AlertTriangle, CheckCircle, Info, Calendar } from 'lucide-react'; 
import Spinner from '../../components/Spinner';
import api from '../../api';

const getStatusChip = (status) => {
    switch (status) {
        case 'Đã xử lý':
            return 'bg-green-100 text-green-700 ring-green-500/10'; 
        case 'Đang xử lý':
            return 'bg-yellow-100 text-yellow-700 animate-pulse ring-yellow-500/10';
        case 'Chờ xác nhận':
            return 'bg-slate-100 text-slate-700 ring-slate-500/10';
        case 'Lỗi':
            return 'bg-red-100 text-red-700 ring-red-500/10';
        case 'An toàn':
            return 'bg-blue-100 text-blue-700 ring-blue-500/10';
        case 'Cảnh báo':
            return 'bg-orange-100 text-orange-700 ring-orange-500/10'; 
        default:
            return 'bg-slate-100 text-slate-700 ring-slate-500/10';
    }
};

const getPlanTypeIcon = (type) => {
    const normalizedType = type.toLowerCase().replace(/\s/g, '');
    if (normalizedType.includes('nước')) return { Icon: Droplet, color: 'text-blue-600', bg: 'bg-blue-50' };
    if (normalizedType.includes('bónphân')) return { Icon: Leaf, color: 'text-green-600', bg: 'bg-green-50' };
    if (normalizedType.includes('giámsát') || normalizedType.includes('xửlý') || normalizedType.includes('treatment')) return { Icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' };
    return { Icon: Info, color: 'text-indigo-600', bg: 'bg-indigo-50' };
};

const HistoryPage = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedItem, setSelectedItem] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);

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

    const handleRowClick = async (item) => {
        setDetailLoading(true);
        setSelectedItem({ ...item, plan: null, type: item.type }); 
        try {
            const res = await api.get(`/user/history/${item.id}`);
            setSelectedItem(prev => ({ ...prev, ...res.data }));
        } catch (err) {
            console.error(err);
            const errorMessage = err.response?.data?.error || "Không thể tải chi tiết kế hoạch này. Có thể kế hoạch đang chờ xử lý hoặc chưa được lưu.";
            alert(errorMessage);
            setSelectedItem(null); 
        } finally {
            setDetailLoading(false);
        }
    };

    const renderModal = () => {
        if (!selectedItem) return null;
        const plan = selectedItem.plan || {};
        const type = selectedItem.type; 
        const { Icon: TypeIcon, color: typeColor, bg: typeBg } = getPlanTypeIcon(type);

        const normalizedType = type.toLowerCase().replace(/\s/g, '');

        const renderSectionTitle = (title, Icon, customColor = 'text-indigo-600') => (
            <div className="flex items-center space-x-2 font-bold mb-3 pt-4 border-t border-slate-200 first:border-t-0">
                <Icon size={20} className={customColor} />
                <h3 className={`text-lg text-slate-800 ${customColor}`}>{title}</h3>
            </div>
        );
        
        const renderDetailCard = (title, content, bgColor = 'bg-slate-50', customClasses = '') => (
            <div className={`p-4 rounded-lg border border-slate-200 ${bgColor} ${customClasses}`}>
                <p className="text-sm font-semibold text-slate-700 mb-1">{title}</p>
                {typeof content === 'string' ? (
                    <p className="text-sm text-slate-600 whitespace-pre-wrap">{content}</p>
                ) : content}
            </div>
        );

        const renderWaterPlan = () => (
            <div className="space-y-4">
                {renderSectionTitle("Đánh giá & Khuyến nghị", Droplet, 'text-blue-600')}
                {plan.current_assessment && renderDetailCard(
                    "Đánh giá hiện tại", 
                    plan.current_assessment, 
                    'bg-blue-50', 
                    'border-blue-200'
                )}
                {plan.main_recommendation && renderDetailCard(
                    "Khuyến nghị chính", 
                    plan.main_recommendation, 
                    'bg-green-50', 
                    'border-green-200 font-medium text-green-700'
                )}
                
                {plan.reason && renderDetailCard(
                    "Cơ sở lý luận", 
                    plan.reason, 
                    'bg-yellow-50', 
                    'border-yellow-200 italic'
                )}
                
                {plan.water_amount_detail && renderDetailCard(
                    "Chi tiết lượng nước / Mực nước mục tiêu", 
                    plan.water_amount_detail, 
                    'bg-indigo-50', 
                    'border-indigo-200'
                )}
                
                {plan.three_day_plan && (
                    <>
                        {renderSectionTitle("Kế hoạch 3 ngày tới", History, 'text-slate-600')}
                        <ul className="bg-slate-50 p-4 rounded-lg space-y-2 border border-slate-200">
                            {Object.entries(plan.three_day_plan).map(([key, action]) => (
                                <li key={key} className="flex items-start text-sm">
                                    <span className="font-medium text-slate-800 min-w-[120px] capitalize mr-2 flex-shrink-0">{key.replace(/_/g, ' ')}:</span> 
                                    <span className="text-slate-600 flex-grow">{action}</span>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
        );

        const renderFertilizerPlan = () => (
            <div className="space-y-4">
                {renderSectionTitle("Tóm tắt chung & Hành động", Leaf, 'text-green-600')}
                {plan.main_message && renderDetailCard(
                    "Tóm tắt hành động chính", 
                    plan.main_message, 
                    'bg-green-50', 
                    'border-green-200 font-medium text-green-700'
                )}
                
                {plan.analysis && (
                    <>
                        {renderSectionTitle("Phân tích Nhu cầu & Thời điểm", Zap, 'text-yellow-600')}
                        {plan.analysis.nutrient_need_assessment && renderDetailCard(
                            "Nhu cầu Dinh dưỡng", 
                            plan.analysis.nutrient_need_assessment, 
                            'bg-yellow-50', 
                            'border-yellow-200'
                        )}
                        {plan.analysis.optimal_timing_summary && renderDetailCard(
                            "Thời điểm Tối ưu (Thời tiết/IoT)", 
                            plan.analysis.optimal_timing_summary, 
                            'bg-blue-50', 
                            'border-blue-200 italic'
                        )}
                    </>
                )}
                
                {renderSectionTitle(`Chi tiết Giai đoạn: ${plan.stage_name}`, Leaf, 'text-emerald-600')}
                <div className="space-y-6">
                    {(plan.fertilizer_stage_detail || []).map((stage, index) => (
                        <div key={index} className="bg-white p-5 rounded-xl shadow-lg border-t-4 border-emerald-500">
                            <h4 className="font-bold text-xl text-slate-800 mb-1 flex items-center">
                                <Calendar size={20} className="text-emerald-600 mr-2"/>
                                <span className="text-lg font-bold text-emerald-700">Lần bón {index + 1}:</span> {stage.timing} 
                            </h4>
                            <p className="text-sm text-slate-500 italic mb-3">Mục tiêu: {stage.objective}</p>

                            {stage.key_indicators && (
                                <p className="text-sm text-blue-700 mb-2 p-2 bg-blue-50 rounded-md">
                                    <strong className="text-blue-800">Chỉ báo hình thái:</strong> {stage.key_indicators}
                                </p>
                            )}

                            <div className="mt-4 space-y-3">
                                {(stage.fertilizers || []).map((f, fIndex) => (
                                    <div key={fIndex} className="p-3 bg-indigo-50 rounded-md text-sm border border-indigo-200">
                                        <strong className="text-indigo-700 text-base">{f.type}</strong>
                                        <ul className="list-disc list-inside ml-2 mt-1 text-slate-600">
                                            <li>Liều lượng/Tổng lượng: **{f.quantity_kg} kg**</li>
                                            <li>HD Pha/Liều đề nghị: {f.recommended_dosage_per_unit}</li>
                                            <li>Chi tiết tính toán: {f.calculation_details}</li>
                                            <li>Hướng dẫn kỹ thuật: {f.instructions}</li>
                                        </ul>
                                    </div>
                                ))}
                            </div>

                            {stage.important_notes && (
                                <p className="text-xs mt-3 text-orange-700 italic border-t pt-2 border-orange-100">
                                    <AlertTriangle size={14} className="inline mr-1"/> **Lưu ý:** {stage.important_notes}
                                </p>
                            )}
                        </div>
                    ))}
                </div>
                
                {plan.additional_advice && (
                    <>
                        {renderSectionTitle("Tư vấn bổ sung & Giai đoạn tiếp theo", Info, 'text-orange-600')}
                        {renderDetailCard(
                            "Lời khuyên quản lý chung", 
                            plan.additional_advice, 
                            'bg-orange-50', 
                            'border-orange-200'
                        )}
                    </>
                )}
                {plan.next_key_stage && (
                    <p className="text-sm font-bold text-indigo-600 mt-4 p-2 bg-slate-50 rounded-md">
                        Giai đoạn quan trọng tiếp theo: <span className="font-normal text-slate-700">{plan.next_key_stage}</span>
                    </p>
                )}
            </div>
        );

        const renderTreatmentPlan = () => (
            <div className="space-y-4">
                {plan.analysis && (
                    <>
                        {renderSectionTitle("Phân tích & Đánh giá", AlertTriangle, 'text-red-600')} 
                        {plan.analysis.risk_assessment && renderDetailCard(
                            "Đánh giá rủi ro", 
                            plan.analysis.risk_assessment, 
                            'bg-red-50', 
                            'border-red-200 text-red-700'
                        )}
                        {plan.analysis.weather_summary && renderDetailCard(
                            "Tổng quan thời tiết", 
                            plan.analysis.weather_summary, 
                            'bg-blue-50', 
                            'border-blue-200 italic'
                        )}
                    </>
                )}

                {plan.treatment_plan && (
                    <>
                        {renderSectionTitle("Kế hoạch xử lý chính", CheckCircle, 'text-indigo-600')} 
                        <div className="p-4 bg-indigo-100 rounded-lg border-l-4 border-indigo-600 text-base font-semibold text-indigo-800">
                            {plan.treatment_plan.main_message}
                        </div>

                        {plan.treatment_plan.drug_info && (
                            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-md text-sm">
                                <strong className="text-slate-800 flex items-center mb-2"><Zap size={16} className="text-indigo-500 mr-2"/>Thông tin Thuốc đề xuất:</strong>
                                <ul className="list-none space-y-1 ml-0 text-slate-600">
                                    <li><span className="font-medium min-w-[100px] inline-block">Sản phẩm:</span> **{plan.treatment_plan.drug_info["sản_phẩm_tham_khảo"]}** </li>
                                    <li><span className="font-medium min-w-[100px] inline-block">Hoạt chất:</span> {plan.treatment_plan.drug_info["hoạt_chất"]}</li>
                                    <li><span className="font-medium min-w-[100px] inline-block">Liều lượng:</span> {plan.treatment_plan.drug_info["liều_lượng"]}</li>
                                    <li><span className="font-medium min-w-[100px] inline-block">Cách dùng:</span> {plan.treatment_plan.drug_info["cách_dùng"]}</li>
                                </ul>
                            </div>
                        )}

                        {plan.treatment_plan.optimal_spray_day && (
                            <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm shadow-sm flex items-start space-x-2">
                                <Calendar size={18} className="text-green-700 mt-0.5 flex-shrink-0"/>
                                <div>
                                    <strong className="text-green-800">Thời điểm phun tối ưu:</strong> {plan.treatment_plan.optimal_spray_day.session} ngày **{plan.treatment_plan.optimal_spray_day.date}**
                                    <p className="italic text-slate-600 mt-1 text-xs">Lý do: {plan.treatment_plan.optimal_spray_day.reason}</p>
                                </div>
                            </div>
                        )}

                        {plan.treatment_plan.additional_actions?.length > 0 && (
                            <div className="p-4 bg-slate-50 border border-slate-200 rounded-md">
                                <strong className="text-slate-800 flex items-center mb-2"><CheckCircle size={16} className="text-slate-500 mr-2"/>Hành động bổ sung:</strong>
                                <ul className="list-disc list-inside ml-4 text-sm space-y-1 text-slate-600">
                                    {plan.treatment_plan.additional_actions.map((action, index) => (
                                        <li key={index}>{action}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                )}
            </div>
        );

        return (
            <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 transition-opacity duration-300">
                <div className="bg-white p-6 rounded-xl w-full max-w-4xl shadow-2xl relative animate-zoom-in max-h-[95vh] overflow-y-auto transform transition-all duration-300">
                    <button 
                        onClick={() => setSelectedItem(null)} 
                        className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 bg-slate-100 p-2 rounded-full transition-colors z-10"
                        aria-label="Đóng chi tiết kế hoạch"
                    >
                        <X size={20} />
                    </button>

                    <header className="mb-6 pb-4 border-b border-indigo-100 flex items-center space-x-3">
                        <div className={`p-3 rounded-full ${typeBg}`}>
                            <TypeIcon size={24} className={typeColor} />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-slate-500">Chi tiết kế hoạch</p>
                            <h2 className="text-3xl font-extrabold text-slate-800">
                                {type}
                            </h2>
                        </div>
                    </header>

                    {detailLoading ? (
                        <div className="flex justify-center py-12"><Spinner /></div>
                    ) : (
                        <div className="space-y-6 text-slate-700">
                            {plan.error ? (
                                <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert">
                                    <p className="font-bold text-lg">Lỗi Dữ Liệu Kế Hoạch</p>
                                    <p>{plan.error}</p>
                                </div>
                            ) : (
                                <>
                                    {(normalizedType.includes("nước") || normalizedType.includes("water")) && renderWaterPlan()}
                                    {(normalizedType.includes("phân") || normalizedType.includes("fertilizer") || normalizedType.includes("bonphan")) && renderFertilizerPlan()}
                                    {(normalizedType.includes("xửlý") || normalizedType.includes("treatment") || normalizedType.includes("giámsát")) && renderTreatmentPlan()}
                                    {(type.includes("Hỏi đáp chung") || type.includes("general")) && (
                                        <div className="bg-blue-50 border-l-4 border-blue-500 text-blue-700 p-4 rounded-md">
                                            <p className="font-bold">Đây là phiên Hỏi đáp chung.</p>
                                            <p>Chi tiết hội thoại có thể được xem tại trang Chi tiết Phiên.</p>
                                        </div>
                                    )}
                                    {(!plan.main_recommendation && !plan.fertilization_stages && !plan.analysis && type !== "Hỏi đáp chung") && (
                                        <div className="text-center p-8 bg-slate-50 rounded-lg border border-slate-200">
                                            <Frown size={40} className="mx-auto mb-3 text-slate-500" />
                                            <p className="text-slate-500 font-medium">
                                                Không có dữ liệu chi tiết cấu trúc rõ ràng cho loại kế hoạch **{type}** này.
                                            </p>
                                            <details className="mt-4 text-xs text-slate-400 cursor-pointer">
                                                <summary>Xem dữ liệu thô (Dành cho nhà phát triển)</summary>
                                                <pre className="mt-2 text-left p-2 bg-slate-100 rounded-md overflow-x-auto">{JSON.stringify(plan, null, 2)}</pre>
                                            </details>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        );
    };

    const renderContent = () => {
        if (loading) return <div className="flex justify-center p-12"><Spinner /></div>;
        if (error) {
            return (
                <div className="text-center p-8 text-red-700 bg-red-50 border border-red-200 rounded-lg flex items-center justify-center space-x-2">
                    <Frown size={24} /> <p className="font-medium">{error}</p>
                </div>
            );
        }
        if (history.length === 0) {
            return (
                <div className="text-center p-12 text-slate-500">
                    <History size={48} className="mx-auto mb-4 text-slate-300" /> 
                    <p className="font-medium">Chưa có hoạt động nào được ghi lại.</p>
                </div>
            );
        }
        return (
            <div className="overflow-x-auto rounded-lg border border-slate-200 shadow-sm">
                <table className="min-w-full text-left table-auto divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="p-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Ngày</th>
                            <th className="p-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Loại Kế hoạch</th>
                            <th className="p-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Kết quả/Đề xuất chính</th>
                            <th className="p-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Rủi ro</th>
                            <th className="p-4 text-xs font-semibold text-slate-600 uppercase tracking-wider text-center">Trạng thái</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-100">
                        {history.map((item) => {
                             const { Icon: TypeIcon, color: typeColor } = getPlanTypeIcon(item.type);
                             return (
                                <tr 
                                    key={item.id}
                                    className="hover:bg-indigo-50/50 cursor-pointer transition duration-150"
                                    onClick={() => handleRowClick(item)}
                                >
                                    <td className="p-4 text-sm text-slate-700 font-medium">{item.date}</td>
                                    <td className="p-4 text-sm font-medium flex items-center space-x-2">
                                        <TypeIcon size={16} className={typeColor}/>
                                        <span className={typeColor}>{item.type}</span>
                                    </td>
                                    <td className="p-4 text-sm text-slate-600 max-w-xs truncate">{item.diagnosis}</td>
                                    <td className="p-4 text-sm text-slate-600">{item.risk}</td>
                                    <td className="p-4 text-center">
                                        <span className={`px-3 py-1 text-xs font-semibold rounded-full ring-1 ${getStatusChip(item.status)}`}>
                                            {item.status}
                                        </span>
                                    </td>
                                </tr>
                             );
                        })}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div className="p-6 md:p-8 min-h-screen bg-slate-50 animate-fade-in">
            <h1 className="text-3xl font-extrabold text-slate-800 mb-8 border-b pb-2">Lịch Sử Hoạt Động</h1>
            <div className="bg-white p-4 md:p-6 rounded-xl shadow-lg">
                {renderContent()}
            </div>
            {renderModal()}
        </div>
    );
};

export default HistoryPage;