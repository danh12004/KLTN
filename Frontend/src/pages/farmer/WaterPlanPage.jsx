import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Droplet, Frown, Target, Send, Zap, AlertTriangle } from 'lucide-react';
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

    const blueDotIcon = L.divIcon({ 
        className: 'custom-blue-dot-icon',
        html: '<div style="background-color: #2563EB; width: 10px; height: 10px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>', 
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
                    icon={blueDotIcon} 
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
    const sizeClasses = { sm: 'w-6 h-6 border-2 border-t-2', md: 'w-10 h-10 border-4 border-t-4' }; 
    return (
        <div className={`animate-spin rounded-full border-slate-200 border-t-blue-600 ${sizeClasses[size]}`}></div>
    );
};

const DayPlanCard = ({ day, planText }) => (
    <div className="bg-white p-4 rounded-lg border border-blue-200 shadow-sm transition-shadow hover:shadow-md">
        <h3 className="font-bold text-blue-700 text-md mb-2">{day}</h3>
        <p className="text-sm text-slate-600">{planText || 'Chưa có kế hoạch.'}</p>
    </div>
);

const WaterPlanPage = () => {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [gpsData, setGpsData] = useState({ lat: null, lon: null, farmArea: null }); 

    const [userFeedback, setUserFeedback] = useState('');
    const [isUpdating, setIsUpdating] = useState(false);
    const [updateError, setUpdateError] = useState('');

    const [isExecuting, setIsExecuting] = useState(false);
    const [executeMessage, setExecuteMessage] = useState('');
    const [isExecuted, setIsExecuted] = useState(false);
    const [alertInfo, setAlertInfo] = useState({ show: false, type: '', message: '' });

    const showAlert = (type, message, duration = 3000) => {
        setAlertInfo({ show: true, type, message });
        setTimeout(() => setAlertInfo({ show: false, type: '', message: '' }), duration);
    };

    useEffect(() => {
        let interval;
        if (isExecuting && plan?.conversation_id) {
            interval = setInterval(async () => {
                try {
                    const res = await api.get(`/plan/status/${plan.conversation_id}`);
                    const status = res.data.status;
                    if (status === "Đã xử lý" || status.startsWith("Lỗi")) {
                        setIsExecuting(false);
                        setExecuteMessage(`Trạng thái: ${status}`);
                        showAlert('success', `Kế hoạch đã ${status.toLowerCase()}`);
                        clearInterval(interval);
                        if (status === "Đã xử lý") setIsExecuted(true);
                    }
                } catch (e) {
                    console.error("Lỗi khi polling trạng thái:", e);
                    clearInterval(interval);
                    setIsExecuting(false);
                }
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [isExecuting, plan]);

    const loadPlan = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const response = await api.get('/user/notifications/latest?plan_type=water');
            const latestPlan = response.data;

            if (latestPlan && latestPlan.plan_type === "Quản lý nước" && latestPlan.conversation_id) {
                const statusExec = latestPlan.status === "Đã xử lý" ? "Đã xử lý" : "Chưa xử lý";
                const finalPlan = { ...latestPlan, status_execution: statusExec };
                setPlan(finalPlan);

                const lat = finalPlan?.action_details_for_system?.gps_data?.lat;
                const lon = finalPlan?.action_details_for_system?.gps_data?.lon;
                const farmArea = finalPlan?.action_details_for_system?.farm_area;
                setGpsData({ lat, lon, farmArea });

                if (statusExec === "Đã xử lý") {
                    setIsExecuted(true);
                    showAlert('warning', 'Kế hoạch này đã được xử lý, không thể chỉnh sửa hoặc thực thi lại.');
                    setExecuteMessage(`Kế hoạch ID ${latestPlan.conversation_id} đã được xử lý.`);
                } else {
                    setExecuteMessage(`Đã tải kế hoạch Quản lý nước mới nhất (ID: ${latestPlan.conversation_id}).`);
                }
            } else {
                setExecuteMessage('Chưa có kế hoạch Quản lý nước nào được tạo gần đây.');
            }

        } catch (err) {
            console.error("Lỗi khi tải thông báo mới nhất:", err);
            setExecuteMessage('Lỗi kết nối hoặc chưa có kế hoạch Quản lý nước mới nhất.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadPlan();
    }, [loadPlan]);

    const generatePlan = async () => {
        if (isExecuting || isUpdating) {
            showAlert('warning', 'Đang có tiến trình khác đang chạy. Vui lòng chờ...');
            return;
        }

        setLoading(true);
        setError('');
        setPlan(null);
        setExecuteMessage('');
        setIsExecuted(false);
        try {
            const response = await api.get('/farm/water-plan');
            const newPlan = { ...response.data, status_execution: "Chưa xử lý" };
            setPlan(newPlan);
            
            const lat = newPlan?.action_details_for_system?.gps_data?.lat || gpsData.lat;
            const lon = newPlan?.action_details_for_system?.gps_data?.lon || gpsData.lon;
            const farmArea = newPlan?.action_details_for_system?.farm_area || gpsData.farmArea;
            setGpsData({ lat, lon, farmArea });

            setExecuteMessage('Kế hoạch Quản lý nước mới đã được tạo.');
            showAlert('success', 'Tạo kế hoạch tưới tiêu thành công!');
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Không thể tạo kế hoạch tưới tiêu.';
            setError(errorMessage);
            showAlert('error', errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const updatePlanFromFeedback = async () => {
        if (isUpdating) {
            showAlert('warning', 'Đang cập nhật kế hoạch, vui lòng chờ...');
            return;
        }

        if (isExecuted) {
            setUpdateError('Kế hoạch đã được thực thi, không thể điều chỉnh phản hồi nữa.');
            showAlert('error', 'Kế hoạch đã được thực thi, vui lòng tạo kế hoạch mới.');
            return;
        }

        if (!userFeedback.trim() || !plan?.conversation_id) {
            setUpdateError('Vui lòng nhập phản hồi và đảm bảo đã có kế hoạch.');
            showAlert('warning', 'Bạn cần nhập phản hồi và đảm bảo có kế hoạch trước.');
            return;
        }

        setIsUpdating(true);
        setUpdateError('');
        try {
            const response = await api.post('/farm/water-plan/update', {
                conversation_id: plan.conversation_id,
                user_message: userFeedback,
            });
            const updatedPlan = { ...response.data, status_execution: plan.status_execution || "Chưa xử lý" };
            setPlan(updatedPlan);
            setUserFeedback('');
            setExecuteMessage('Kế hoạch đã được cập nhật thành công!');
            showAlert('success', 'Cập nhật kế hoạch thành công!');
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Lỗi khi cập nhật kế hoạch.';
            setUpdateError(errorMessage);
            showAlert('error', errorMessage);
        } finally {
            setIsUpdating(false);
        }
    };

    const executePlan = async () => {
        if (isExecuting) {
            showAlert('warning', 'Lệnh thực thi đang được xử lý, vui lòng chờ...');
            return;
        }
        if (!plan?.conversation_id) {
            showAlert('warning', 'Không có kế hoạch để thực thi.');
            return;
        }
        if (isExecuted) {
            showAlert('warning', 'Kế hoạch này đã được thực thi trước đó.');
            return;
        }

        setIsExecuting(true);
        setExecuteMessage('');
        try {
            const response = await api.post('/plan/execute', {
                conversation_id: plan.conversation_id,
                plan_type: 'water',
            });
            const msg = response.data?.message || 'Lệnh thực thi đã được gửi.';
            const status = response.data?.status || 'unknown';
            setExecuteMessage(`${msg} (Trạng thái: ${status})`);
            showAlert('success', msg);
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Lỗi khi gửi lệnh thực thi.';
            setExecuteMessage(errorMessage);
            showAlert('error', errorMessage);
            setIsExecuting(false);
        }
    };

    return (
        <div className="animate-fade-in font-sans relative">
            {alertInfo.show && (
                <div
                    className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 text-white 
                    ${alertInfo.type === 'success' ? 'bg-green-600' :
                        alertInfo.type === 'error' ? 'bg-red-600' :
                            'bg-yellow-500'}`}
                >
                    <AlertTriangle size={18} />
                    <span className="font-medium text-sm">{alertInfo.message}</span>
                </div>
            )}

            <h1 className="text-3xl font-bold text-slate-800 mb-6 flex items-center">
                <Droplet size={32} className="text-blue-500 mr-2" /> Kế Hoạch Quản Lý Nước
            </h1>
            
            <h2 className="text-2xl font-bold text-slate-700 mb-4 border-b pb-2 flex items-center">
                <Target size={24} className="text-blue-500 mr-2" /> Vị Trí Cánh Đồng ({gpsData.lat || 'Đang tải'}, {gpsData.lon || 'Đang tải'})
            </h2>
            <div className="mb-8">
                <FarmMap lat={gpsData.lat} lon={gpsData.lon} farmArea={gpsData.farmArea} />
            </div>

            <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center">
                <h2 className="text-xl font-bold text-slate-700">Tạo Kế hoạch Tưới tiêu Thông minh</h2>
                <p className="text-slate-500 mt-2 mb-6 max-w-xl mx-auto">
                    Dựa trên dữ liệu cảm biến IoT và thời tiết, hệ thống sẽ đề xuất kế hoạch tưới tiêu tối ưu.
                </p>
                <button
                    onClick={generatePlan}
                    disabled={loading || isExecuting || isUpdating}
                    className="bg-blue-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-slate-400 flex items-center justify-center mx-auto cursor-pointer shadow-lg shadow-blue-300/50"
                >
                    {loading && !plan ? <Spinner size="sm" /> : 'Lấy Kế hoạch Tưới tiêu'}
                </button>
            </div>

            {error && (
                <div className="mt-8 text-center p-6 bg-red-50 text-red-700 rounded-lg shadow-md border border-red-200">
                    <Frown className="mx-auto mb-2" /> {error}
                </div>
            )}
            
            {executeMessage && !loading && (
                <div className="mt-8 text-center p-4 rounded-xl shadow-md border bg-blue-100 text-blue-700 border-blue-300">
                    <p className="font-medium">{executeMessage}</p>
                </div>
            )}

            {plan && (
                <div className="mt-8 bg-white p-8 rounded-xl shadow-xl border border-blue-100">
                    <h2 className="text-2xl font-bold text-slate-800 mb-4 text-center border-b pb-3">Đề xuất Quản lý nước</h2>
                    
                    {isExecuted && (
                        <div className="mb-4 p-4 bg-yellow-100 text-yellow-800 rounded-lg border border-yellow-300 flex items-center space-x-2">
                            <AlertTriangle size={20} />
                            <span className="font-semibold text-sm">
                                Kế hoạch này **đã được thực thi**. Vui lòng tạo kế hoạch mới nếu muốn thay đổi.
                            </span>
                        </div>
                    )}
                    <div className="mb-6 p-6 rounded-xl bg-blue-50 border border-blue-400 shadow-2xl shadow-blue-400/30">
                        <h3 className="text-lg font-bold text-blue-700 mb-2 uppercase flex items-center">
                            <Zap size={20} className="mr-2" /> LỆNH THỰC THI NGAY
                        </h3>
                        <p className="text-3xl font-extrabold text-blue-800 mb-3 leading-tight">
                            {plan.immediate_command || plan.main_recommendation || 'Chờ quyết định cuối cùng'}
                        </p>
                        <p className="text-slate-700 text-sm border-t border-blue-200 pt-2 mt-2">
                            <strong>Lý do:</strong> {plan.reason || 'Chưa có giải thích chi tiết.'}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <DayPlanCard day="Hôm nay" planText={plan.three_day_plan?.today} />
                        <DayPlanCard day="Ngày mai" planText={plan.three_day_plan?.tomorrow} />
                        <DayPlanCard day="Ngày kia" planText={plan.three_day_plan?.day_after_tomorrow} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
                        <div className="md:col-span-2 bg-slate-50 p-4 rounded-lg border border-slate-200">
                            <h4 className="font-bold text-slate-700 flex items-center mb-2">
                                <Send size={18} className="mr-2 text-indigo-500" />Điều Chỉnh Kế Hoạch
                            </h4>
                            <textarea
                                value={userFeedback}
                                onChange={(e) => setUserFeedback(e.target.value)}
                                placeholder="Ví dụ: 'Tôi muốn nâng mực nước lên 5cm vì tôi dự định bón phân ngày mai.'"
                                className="w-full p-2 border border-slate-300 rounded-md resize-none focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                                rows="3"
                                disabled={isExecuting || isUpdating || isExecuted}
                            ></textarea>
                            {updateError && <p className="text-red-500 text-xs mt-1">{updateError}</p>}
                            <button
                                onClick={updatePlanFromFeedback}
                                disabled={isUpdating || isExecuting || !userFeedback.trim() || isExecuted}
                                className="mt-3 w-full bg-indigo-500 text-white font-bold py-2 rounded-lg hover:bg-indigo-600 transition-colors disabled:bg-slate-400 text-sm flex items-center justify-center"
                            >
                                {isUpdating ? <Spinner size="sm" /> : 'Cập Nhật Kế Hoạch'}
                            </button>
                        </div>

                        <div className="md:col-span-1 flex items-stretch">
                            <button
                                onClick={executePlan}
                                disabled={isExecuting || isUpdating || isExecuted}
                                className={`w-full text-white font-extrabold py-4 rounded-lg transition-colors flex flex-col items-center justify-center shadow-lg text-base uppercase
                                ${isExecuting || isUpdating || isExecuted
                                    ? 'bg-slate-400 cursor-not-allowed'
                                    : 'bg-green-600 hover:bg-green-700 cursor-pointer shadow-green-300/50'
                                }`}
                            >
                                {isExecuting ? (
                                    <>
                                        <Spinner size="sm" />
                                        <span className="mt-2">Đang Thực Thi...</span>
                                    </>
                                ) : (
                                    <>
                                        <Zap size={24} />
                                        <span className="mt-1 cursor-pointer">
                                            {isExecuted ? 'Đã Thực Thi' : 'Thực Thi LỆNH NÀY'}
                                        </span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default WaterPlanPage;