import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'; 
import {
    Leaf, Frown, Tractor, Send, Zap, AlertTriangle, Clock,
    Target, Info, Feather, ChevronRight, Check, GitCompare,
    RotateCcw, CheckCircle, XCircle
} from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import api from '../../api';

if (L && L.Icon && L.Icon.Default) {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });
}

const ChangeView = ({ center, zoom }) => {
    if (useMap) {
        const map = useMap();
        map.setView(center, zoom);
    }
    return null;
}

const FarmMap = ({ lat, lon, farmArea }) => {
    if (!lat || !lon || !MapContainer || !L) {
        return <div className="p-4 bg-red-100 text-red-700 rounded-xl">Không có dữ liệu GPS hoặc thư viện bản đồ chưa được tải.</div>;
    }

    const position = [lat, lon];
    const initialZoom = 15;
    
    const markerRef = useRef(null);

    const greenDotIcon = L.divIcon({
        className: 'custom-green-dot-icon',
        html: '<div style="background-color: #059669; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>', 
        iconSize: [14, 14],
        iconAnchor: [7, 7],
    });

    const eventHandlers = useMemo(
        () => ({
            mouseover() {
                if (markerRef.current) {
                    markerRef.current.openPopup();
                }
            },
            mouseout() {
                if (markerRef.current) {
                    markerRef.current.closePopup();
                }
            },
        }),
        [],
    );

    return (
        <div className="rounded-xl overflow-hidden shadow-xl border border-slate-200 h-[400px]">
            <MapContainer 
                center={position} 
                zoom={initialZoom} 
                scrollWheelZoom={true} 
                className="h-full w-full"
                key={`${lat}-${lon}`}
            >
                <ChangeView center={position} zoom={initialZoom} />
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                <Marker 
                    position={position} 
                    icon={greenDotIcon} 
                    ref={markerRef} 
                    eventHandlers={eventHandlers} 
                > 
                    <Popup>
                        <strong className="text-red-600">Vị Trí Bệnh ({lat}, {lon})</strong>
                        <br />
                        Khu vực: {farmArea || 'Đang cập nhật'}
                    </Popup>
                </Marker>
            </MapContainer>
        </div>
    );
};

const Spinner = ({ size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-6 h-6 border-2 border-t-2',
        md: 'w-10 h-10 border-4 border-t-4',
    };
    return (
        <div className={`animate-spin rounded-full border-slate-200 border-t-emerald-600 ${sizeClasses[size]}`}></div>
    );
};

const InfoItem = ({ icon, label, value }) => {
    if (!value) return null;

    return (
        <div className="flex items-start p-3 bg-white rounded-lg shadow-sm border border-slate-100">
            <span className="text-slate-400 mt-1 mr-3 flex-shrink-0">
                {icon || <Info size={20} />}
            </span>
            <div>
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
                <p className="text-sm text-slate-800 font-semibold mt-1">{value}</p>
            </div>
        </div>
    );
};

const PlanDisplay = ({ plan, title, titleIcon, bgColor = 'bg-white' }) => {
    if (!plan) return null;

    const analysis = plan.analysis || {};
    const fertilizerDetails = plan.fertilizer_stage_detail || [];

    return (
        <div className={`p-6 md:p-10 rounded-2xl shadow-2xl border ${bgColor} border-emerald-200`}>
            <h2 className="text-3xl font-extrabold text-slate-800 mb-4 border-b pb-4 flex items-center">
                {titleIcon || <Leaf size={28} className="text-amber-500 mr-2" />} {title}
            </h2>

            {plan.main_message && (
                <div className="p-4 mb-6 bg-emerald-50 border-l-4 border-emerald-500 rounded-lg shadow-inner">
                    <p className="font-semibold text-lg text-emerald-800 flex items-center">
                        <Zap size={20} className="mr-2" />
                        {plan.main_message}
                    </p>
                </div>
            )}

            <h3 className="text-xl font-bold text-slate-700 mt-6 mb-3 border-b border-slate-100 pb-2">
                <Info size={20} className="mr-2 inline text-blue-500" /> Phân Tích & Thời Điểm
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-bold text-blue-700 mb-2 flex items-center">
                        <Feather size={18} className="mr-2" /> Nhu Cầu Dinh Dưỡng
                    </h4>
                    <p className="text-sm text-slate-700">{analysis.nutrient_need_assessment || 'Chưa có phân tích.'}</p>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                    <h4 className="font-bold text-yellow-700 mb-2 flex items-center">
                        <Clock size={18} className="mr-2" /> Thời Điểm Bón Tối Ưu
                    </h4>
                    <p className="text-sm text-slate-700">{analysis.optimal_timing_summary || 'Chưa có phân tích.'}</p>
                </div>
            </div>

            {fertilizerDetails.map((stageDetail, stageIndex) => (
                <div key={stageIndex} className="bg-slate-50 p-6 rounded-xl shadow-inner border border-slate-200 mb-6">
                    <h3 className="text-2xl font-extrabold text-slate-700 mb-4 border-b pb-3">
                        <Target size={22} className="mr-2 inline text-indigo-500" /> Kế Hoạch Bón Cụ Thể
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                        <InfoItem icon={<Clock size={20} />} label="Khoảng Ngày Bón" value={stageDetail.timing} />
                        <InfoItem icon={<Target size={20} />} label="Mục Tiêu" value={stageDetail.objective} />
                        <InfoItem icon={<Feather size={20} />} label="Chỉ Số Nhận Biết" value={stageDetail.key_indicators} />
                    </div>

                    <div className="space-y-4 pt-4 border-t border-slate-200">
                        {(stageDetail.fertilizers || []).map((fertilizer, fertIndex) => (
                            <div key={fertIndex} className="p-4 bg-white rounded-lg border border-emerald-200 shadow-sm hover:shadow-md transition-shadow">
                                <p className="font-extrabold text-lg text-emerald-800 mb-3 uppercase flex items-center">
                                    <Tractor size={20} className="mr-2 text-emerald-600" /> {fertilizer.type}
                                </p>
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-sm">
                                    <div className="border-r border-slate-100 pr-4">
                                        <InfoItem
                                            icon={<Leaf size={20} />}
                                            label="Liều Lượng Tổng (KG)"
                                            value={<span className="text-xl text-red-600 font-extrabold">{fertilizer.quantity_kg} kg</span>}
                                        />
                                        <p className="text-xs text-slate-500 mt-1 pl-10">
                                            <span className="font-medium text-slate-700">Gốc:</span> {fertilizer.recommended_dosage_per_unit} - <span className="font-medium text-slate-700">Tính toán:</span> {fertilizer.calculation_details}
                                        </p>
                                    </div>
                                    <div className="lg:pl-4">
                                        <p className="font-medium text-slate-500 uppercase tracking-wider mb-2">Hướng Dẫn Kỹ Thuật</p>
                                        <p className="text-slate-800 leading-relaxed text-sm">{fertilizer.instructions}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {stageDetail.important_notes && (
                        <div className="mt-4 bg-amber-100 p-3 rounded-lg border border-amber-300 text-amber-800">
                            <p className="font-bold text-sm flex items-center">
                                <AlertTriangle size={16} className="mr-2" /> Lưu Ý Quan Trọng:
                            </p>
                            <p className="text-sm mt-1">{stageDetail.important_notes}</p>
                        </div>
                    )}
                </div>
            ))}

            {plan.next_key_stage && (
                <div className="mt-6 p-4 bg-indigo-50 rounded-xl border border-indigo-200 text-indigo-800 shadow-md flex items-center justify-between">
                    <p className="font-bold text-lg flex items-center">
                        <ChevronRight size={20} className="mr-2" /> Giai Đoạn Tiếp Theo:
                    </p>
                    <p className="font-extrabold text-xl">{plan.next_key_stage}</p>
                </div>
            )}
        </div>
    );
};


const FertilizerPlanPage = () => {
    const [originalPlan, setOriginalPlan] = useState(null);
    const [suggestedPlan, setSuggestedPlan] = useState(null);
    const [gpsData, setGpsData] = useState({ lat: null, lon: null, farmArea: null }); 
    const [conversationId, setConversationId] = useState(null);
    const [status, setStatus] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [userFeedback, setUserFeedback] = useState('');
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateError, setUpdateError] = useState('');
    const [isExecuting, setIsExecuting] = useState(false);
    const [executeMessage, setExecuteMessage] = useState('');

    const [isActing, setIsActing] = useState(false);
    const [isExecuted, setIsExecuted] = useState(false);
    const [alertInfo, setAlertInfo] = useState({ show: false, type: '', message: '' });

    const location = useLocation();
    const showAlert = (type, message, duration = 3000) => {
        setAlertInfo({ show: true, type, message });
        setTimeout(() => setAlertInfo({ show: false, type: '', message: '' }), duration);
    };

    const loadPlanData = useCallback((sessionData, messagePrefix = "") => {
        if (!sessionData || !sessionData.conversation_id) {
            setOriginalPlan(null);
            setSuggestedPlan(null);
            setConversationId(null);
            setStatus('Chưa tải');
            setExecuteMessage('Chưa có kế hoạch bón phân nào. Hãy nhấn "Tạo Kế hoạch Mới".');
            setGpsData({ lat: null, lon: null, farmArea: null });
            setIsExecuted(false);
            setIsExecuting(false);
            return;
        }

        setConversationId(sessionData.conversation_id);
        setStatus(sessionData.status);

        let finalPlan = null;
        let suggested = null;
        let sourcePlan = sessionData; 

        if (sessionData.plan) { 
            suggested = sessionData.plan;
        }
        if (sessionData.original_plan) { 
            finalPlan = sessionData.original_plan;
            sourcePlan = finalPlan;
        }
        
        if (!finalPlan && suggested) {
            finalPlan = suggested;
            sourcePlan = finalPlan;
        }

        if (!finalPlan && sessionData.final_plan_json) {
            try {
                finalPlan = JSON.parse(sessionData.final_plan_json);
                sourcePlan = finalPlan;
            } catch (e) {
                console.error("Bad final_plan_json", e, sessionData.final_plan_json);
            }
        }
        if (!suggested && sessionData.suggested_plan_json) {
            try {
                suggested = JSON.parse(sessionData.suggested_plan_json);
            } catch (e) {
                console.error("Bad suggested_plan_json", e, sessionData.suggested_plan_json);
            }
        }

        let lat = null, lon = null, farmArea = null;
        
        if (sourcePlan?.action_details_for_system?.gps_data) {
            lat = sourcePlan.action_details_for_system.gps_data.lat;
            lon = sourcePlan.action_details_for_system.gps_data.lon;
        } 
        else if (sourcePlan?.gps_data) {
            lat = sourcePlan.gps_data.lat;
            lon = sourcePlan.gps_data.lon;
        }

        if (sourcePlan?.farm_area) { 
            farmArea = sourcePlan.farm_area;
        } else if (sourcePlan?.total_dosage) {
            farmArea = sourcePlan.total_dosage.farm_area;
        } else if (sourcePlan?.action_details_for_system?.total_dosage) {
            farmArea = sourcePlan.action_details_for_system.total_dosage.farm_area;
        }
        
        setGpsData({ lat, lon, farmArea }); 

        let msg = messagePrefix;
        if (suggested && finalPlan && suggested !== finalPlan) { 
            setOriginalPlan(finalPlan);
            setSuggestedPlan(suggested);
            msg += `Đã tải kế hoạch (ID: ${sessionData.conversation_id}) và một gợi ý cập nhật.`;
        } else if (finalPlan) { 
            setOriginalPlan(finalPlan);
            setSuggestedPlan(null);
            msg += `Đã tải kế hoạch (ID: ${sessionData.conversation_id}).`;
        } else {
            setOriginalPlan(null);
            setSuggestedPlan(null);
            msg += 'Chưa có kế hoạch bón phân nào. Hãy nhấn "Tạo Kế hoạch Mới".';
        }
        
        if (sessionData.main_message || (finalPlan && finalPlan.main_message)) {
             setExecuteMessage(sessionData.main_message || finalPlan.main_message);
        } else {
             setExecuteMessage(msg);
        }
        
        if (sessionData.status === "Đang xử lý") {
            setIsExecuting(true);
        } else {
            setIsExecuting(false);
        }

        if (sessionData.status === "Đã xử lý") {
            setIsExecuted(true);
        } else {
            setIsExecuted(false);
        }
    }, []);

    const loadLatestPlan = useCallback(async (isFromNotification = false) => {
        if (!isFromNotification) setLoading(true);
        try {
            const response = await api.get('/user/notifications/latest?plan_type=fertilizer');
            const latestSession = response.data;

            if (latestSession && (latestSession.plan_type === "Bón phân" || latestSession.plan_type === "fertilizer")) {
                loadPlanData(latestSession, "Đã tải: ");
            } else {
                loadPlanData(null);
            }
        } catch (err) {
            if (err.response?.status === 404) {
                loadPlanData(null);
            } else {
                console.error("Lỗi khi tải kế hoạch bón phân mới nhất:", err);
                showAlert('error', 'Không thể tải kế hoạch bón phân gần nhất.');
                setError('Không thể tải kế hoạch bón phân gần nhất.');
            }
        } finally {
            if (!isFromNotification) setLoading(false);
        }
    }, [loadPlanData]);

    useEffect(() => {
        let interval;
        if (isExecuting && conversationId) {
            interval = setInterval(async () => {
                try {
                    const response = await api.get('/user/notifications/latest?plan_type=fertilizer');
                    const latestSession = response.data;

                    if (latestSession && latestSession.conversation_id === conversationId) {
                        loadPlanData(latestSession, "Đã làm mới: ");

                        if (latestSession.status === "Đã xử lý" || latestSession.status.startsWith("Lỗi")) {
                            clearInterval(interval);
                            showAlert(latestSession.status === "Đã xử lý" ? 'success' : 'error', `Kế hoạch đã ${latestSession.status.toLowerCase()}`);
                        }
                    } else {
                        clearInterval(interval);
                    }
                } catch (e) {
                    console.error("Lỗi khi polling plan data:", e);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [isExecuting, conversationId, loadPlanData]);

    useEffect(() => {
        setLoading(true);
        if (location.state?.newNotification) {
            const latestSession = location.state.newNotification;
            if (latestSession && (latestSession.plan_type === "Bón phân" || latestSession.plan_type === "fertilizer")) {
                loadPlanData(latestSession, "Từ thông báo: ");
                setLoading(false);
                return;
            }
        }

        loadLatestPlan(false);
    }, [location.state, loadLatestPlan]);


    const generatePlan = async () => {
        if (loading || isExecuting || isUpdating || isActing) {
            showAlert('warning', 'Đang có tiến trình khác đang chạy. Vui lòng chờ...');
            return;
        }
        setLoading(true);
        setError('');
        setOriginalPlan(null);
        setSuggestedPlan(null);
        setConversationId(null);
        setExecuteMessage('');
        setIsExecuted(false);

        try {
            const response = await api.get('/farm/fertilizer-plan');
            loadPlanData(response.data, "Đã tạo: "); 
            showAlert('success', response.data.plan ? response.data.plan.main_message : "Kế hoạch mới đã được tạo.");

        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Không thể tạo kế hoạch bón phân lúc này. Vui lòng thử lại sau.';
            setError(errorMessage);
            console.error(err);
            showAlert('error', errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const updatePlanFromFeedback = async () => {
        if (isUpdating) {
            showAlert('warning', 'Đang cập nhật, vui lòng chờ...');
            return;
        }

        if (!userFeedback.trim() || !conversationId) {
            setUpdateError('Vui lòng nhập phản hồi và đảm bảo đã có kế hoạch (Tạo kế hoạch trước).');
            showAlert('warning', 'Bạn cần nhập phản hồi và đảm bảo có kế hoạch trước.');
            return;
        }

        setIsUpdating(true);
        setUpdateError('');

        try {
            const response = await api.post('/farm/fertilizer-plan/update', {
                conversation_id: conversationId,
                user_message: userFeedback,
            });

            loadPlanData(response.data, "Đã cập nhật: "); 

            setUserFeedback('');
            const msg = response.data.main_message || 'Kế hoạch đã được cập nhật thành công!';
            showAlert('success', msg);
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Lỗi khi cập nhật kế hoạch. Vui lòng thử lại.';
            setUpdateError(errorMessage);
            showAlert('error', errorMessage);
        } finally {
            setIsUpdating(false);
        }
    };

    const isPlanInFinalState = isExecuted || status === 'Không hành động';

    const handlePlanAction = async (action) => {
        if (isActing || !conversationId || isPlanInFinalState) return;
        setIsActing(true);

        try {
            const response = await api.post('/farm/fertilizer-plan/action', {
                conversation_id: conversationId,
                action: action,
            });

            loadPlanData(response.data, `Đã ${action === 'accept_suggestion' ? 'chấp nhận' : 'từ chối'} gợi ý: `);

            const msg = response.data.main_message;
            showAlert('success', msg);

        } catch (err) {
            const errorMessage = err.response?.data?.error || 'Lỗi khi xử lý hành động.';
            showAlert('error', errorMessage);
        } finally {
            setIsActing(false);
        }
    };

    const executePlan = async () => {
        if (isExecuting) {
            showAlert('warning', 'Lệnh thực thi đang được xử lý hoặc đã được lên lịch, vui lòng chờ...');
            return;
        }

        if (isPlanInFinalState) {
            showAlert('warning', 'Kế hoạch này đã ở trạng thái cuối cùng (Đã xử lý hoặc Không hành động).');
            return;
        }

        if (!conversationId) {
            showAlert('warning', 'Không có kế hoạch để thực thi.');
            return;
        }

        setIsExecuting(true);
        setExecuteMessage('');
        setUpdateError('');

        try {
            const response = await api.post('/plan/execute', {
                conversation_id: conversationId,
                plan_type: 'fertilizer',
            });

            const status_res = response.data?.status;
            let msg = response.data?.message || 'Lệnh thực thi đã được gửi.';

            if (status_res === 'already_executed' || status_res === 'Đã xử lý') {
                msg = `Kế hoạch này đã được thực thi trước đó.`;
                setIsExecuted(true);
                setStatus("Đã xử lý");
                setIsExecuting(false);
            } else if (status_res === 'accepted' || status_res === 'processing') {
                msg = `${response.data.message}`;
                setStatus("Đang xử lý");
            }

            setExecuteMessage(msg);
            showAlert('success', msg);

            if (status_res === 'already_executed') {
                setIsExecuting(false);
            }
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Lỗi khi gửi lệnh thực thi.';
            setExecuteMessage(errorMessage);
            showAlert('error', errorMessage);
            setIsExecuting(false);
        }
    };


    return (
        <div className="animate-fade-in font-sans relative min-h-screen bg-slate-50 pb-16">
            {alertInfo.show && (
                <div
                    className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-2xl flex items-center space-x-3 text-white transition-opacity duration-300
                    ${alertInfo.type === 'success' ? 'bg-green-600' :
                                alertInfo.type === 'error' ? 'bg-red-600' :
                                    'bg-yellow-500'}`}
                >
                    <AlertTriangle size={20} />
                    <span className="font-semibold text-base">{alertInfo.message}</span>
                </div>
            )}

            <div className="max-w-7xl mx-auto p-3">
                <h1 className="text-4xl font-extrabold text-slate-800 mb-2 flex items-center">
                    <Leaf size={32} className="text-emerald-500 mr-3" /> Kế Hoạch Bón Phân
                </h1>
                <p className="text-slate-500 mb-8 text-lg">Tối ưu hóa dinh dưỡng theo từng giai đoạn phát triển của cây lúa.</p>

                <h2 className="text-3xl font-extrabold text-slate-800 mb-4 border-b pb-4 flex items-center">
                    <Target size={28} className="text-emerald-500 mr-2" /> Vị Trí Cánh Đồng ({gpsData.lat || 'Đang tải'}, {gpsData.lon || 'Đang tải'})
                </h2>
                <div className="mb-8">
                    <FarmMap lat={gpsData.lat} lon={gpsData.lon} farmArea={gpsData.farmArea} />
                </div>

                <div className="bg-white p-8 rounded-2xl shadow-lg border border-slate-100 text-center mb-8 hover:shadow-xl transition-shadow">
                    <h2 className="text-2xl font-bold text-slate-700">Tạo Kế Hoạch Bón Phân Thông Minh</h2>
                    <p className="text-slate-500 mt-2 mb-6 max-w-2xl mx-auto">
                        Tận dụng dữ liệu IoT và khí hậu để đề xuất kế hoạch bón phân chính xác nhất cho khu vực của bạn.
                    </p>
                    <button
                        onClick={generatePlan}
                        disabled={loading || isExecuting || isUpdating || isActing}
                        className="bg-emerald-600 text-white font-bold py-3 px-10 rounded-full hover:bg-emerald-700 transition-all disabled:bg-slate-400 flex items-center justify-center mx-auto cursor-pointer shadow-xl shadow-emerald-300/50 transform hover:scale-105"
                    >
                        {loading ? <Spinner size="sm" /> : (
                            <>
                                <Leaf size={20} className="mr-2" />
                                Tạo Kế hoạch Mới Ngay
                            </>
                        )}
                    </button>
                </div>
                
                {loading && (
                    <div className="mt-8 text-center p-6 bg-white text-slate-700 rounded-xl shadow-md border border-slate-200 flex flex-col items-center justify-center">
                        <Spinner size="md" />
                        <p className="mt-4 font-semibold">Đang tải kế hoạch...</p>
                    </div>
                )}

                {!loading && error && (
                    <div className="mt-8 text-center p-6 bg-red-50 text-red-700 rounded-xl shadow-md border border-red-200">
                        <Frown className="mx-auto mb-2" /> {error}
                    </div>
                )}

                {!loading && !error && (
                    <>
                        {executeMessage && !(originalPlan || suggestedPlan) && (
                            <div className={`mt-8 text-center p-4 rounded-xl shadow-md border ${
                                (status === "Không hành động" || executeMessage.includes('Chưa có')) ? 'bg-blue-100 text-blue-700 border-blue-300' :
                                'bg-green-100 text-green-700 border-green-300'
                            }`}>
                                <p className="font-medium">{executeMessage}</p>
                            </div>
                        )}

                        {suggestedPlan && originalPlan && (
                            <div className="mt-8 animate-fade-in">
                                <div className="p-6 bg-yellow-50 border-l-4 border-yellow-500 rounded-lg shadow-lg mb-8 text-center">
                                    <h2 className="text-2xl font-extrabold text-yellow-800 flex items-center justify-center">
                                        <GitCompare size={24} className="mr-3" />
                                        Phát hiện gợi ý cập nhật!
                                    </h2>
                                    <p className="text-yellow-700 mt-2">Dựa trên dữ liệu mới, chúng tôi đề xuất một số thay đổi. Vui lòng xem xét và chọn một hành động.</p>
                                </div>

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                    <PlanDisplay
                                        plan={originalPlan}
                                        title="Kế Hoạch Gốc"
                                        titleIcon={<RotateCcw size={28} className="text-slate-500 mr-2" />}
                                        bgColor="bg-slate-50"
                                    />
                                    <PlanDisplay
                                        plan={suggestedPlan}
                                        title="Kế Hoạch Gợi Ý"
                                        titleIcon={<Zap size={28} className="text-amber-500 mr-2" />}
                                        bgColor="bg-white"
                                    />
                                </div>

                                <div className="mt-8 p-6 bg-white rounded-2xl shadow-xl flex flex-col md:flex-row gap-4 justify-center">
                                    <button
                                        onClick={() => handlePlanAction('reject_suggestion')}
                                        disabled={isActing || isPlanInFinalState} 
                                        className="flex-1 bg-slate-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-slate-700 transition-all disabled:bg-slate-400 flex items-center justify-center text-lg"
                                    >
                                        {isActing ? <Spinner size="sm" /> : <XCircle size={22} className="mr-2" />} Giữ Kế Hoạch Gốc
                                    </button>
                                    <button
                                        onClick={() => handlePlanAction('accept_suggestion')}
                                        disabled={isActing || isPlanInFinalState} 
                                        className="flex-1 bg-green-600 text-white font-bold py-4 px-6 rounded-lg hover:bg-green-700 transition-all disabled:bg-slate-400 flex items-center justify-center text-lg"
                                    >
                                        {isActing ? <Spinner size="sm" /> : <CheckCircle size={22} className="mr-2" />} Chấp Nhận & Cập Nhật Gợi Ý
                                    </button>
                                </div>
                            </div>
                        )}

                        {!suggestedPlan && originalPlan && (
                            <div className="mt-8 animate-fade-in">
                                <PlanDisplay
                                    plan={originalPlan}
                                    title={originalPlan.stage_name || "Kế hoạch Bón phân"}
                                    bgColor="bg-white"
                                />

                                <div className="mt-8 pt-6 border-t border-slate-200 grid grid-cols-1 md:grid-cols-3 gap-6 bg-white p-6 rounded-xl shadow-lg">
                                    <div className="md:col-span-2 bg-slate-100 p-6 rounded-xl border border-slate-200 shadow-inner">
                                        <h4 className="font-bold text-slate-700 flex items-center mb-3 text-lg">
                                            <Send size={20} className="mr-2 text-indigo-500" /> Điều Chỉnh & Phản Hồi
                                        </h4>
                                        <textarea
                                            value={userFeedback}
                                            onChange={(e) => setUserFeedback(e.target.value)}
                                            placeholder={
                                                isPlanInFinalState ? 'Kế hoạch đã được thực thi, không thể chỉnh sửa.' : 
                                                isExecuting ? 'Kế hoạch đang được IOT thực thi, nhưng bạn vẫn có thể gửi phản hồi cập nhật.' :
                                                "Ví dụ: 'Tôi muốn thay loại phân NPK thành loại 16-16-8...'"
                                            }
                                            className="w-full p-3 border border-slate-300 rounded-lg resize-none focus:ring-indigo-500 focus:border-indigo-500 text-sm shadow-sm"
                                            rows="3"
                                            disabled={isUpdating || isPlanInFinalState}
                                        ></textarea>
                                        {updateError && <p className="text-red-500 text-sm mt-2 font-medium">{updateError}</p>}
                                        <button
                                            onClick={updatePlanFromFeedback}
                                            disabled={isUpdating || !userFeedback.trim() || isPlanInFinalState}
                                            className="mt-4 w-full bg-indigo-500 text-white font-bold py-3 rounded-lg hover:bg-indigo-600 transition-colors disabled:bg-slate-400 text-base flex items-center justify-center shadow-md hover:shadow-lg cursor-pointer"
                                        >
                                            {isUpdating ? <Spinner size="sm" /> : 'Gửi Phản Hồi & Cập Nhật'}
                                        </button>
                                    </div>

                                    <div className="md:col-span-1 flex items-stretch">
                                        <button
                                            onClick={executePlan}
                                            disabled={isExecuting || !conversationId || isUpdating || isPlanInFinalState}
                                            className={`w-full text-white font-extrabold py-6 rounded-xl transition-all flex flex-col items-center justify-center shadow-2xl text-lg uppercase transform hover:scale-[1.02]
                                                ${isPlanInFinalState
                                                    ? 'bg-slate-400 cursor-not-allowed'
                                                    : isExecuting
                                                        ? 'bg-yellow-500 cursor-wait'
                                                        : 'bg-green-600 hover:bg-green-700 cursor-pointer shadow-green-400/50'
                                                }`}
                                        >
                                            {isPlanInFinalState ? (
                                                (status === "Không hành động") ? (
                                                    <><XCircle size={24} className="text-white mb-2" /><span>KHÔNG HÀNH ĐỘNG</span></>
                                                ) : (
                                                    <><Check size={24} className="text-white mb-2" /><span>ĐÃ THỰC THI</span></>
                                                )
                                            ) : isExecuting ? (
                                                <><Spinner size="sm" /><span className="mt-3">
                                                    {status === "Đang xử lý" ? "ĐANG LÊN LỊCH..." : "ĐANG GỬI LỆNH..."}
                                                </span></>
                                            ) : (
                                                <><Zap size={30} /><span className="mt-2">THỰC THI KẾ HOẠCH</span><span className="text-xs mt-1 font-medium">(Gửi lệnh đến IoT)</span></>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {conversationId && (
                            <p className="mt-6 text-xs text-slate-400 text-right">
                                ID phiên: {conversationId}
                            </p>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default FertilizerPlanPage;