    import React, { useState, useEffect } from 'react';
    import { useNavigate } from 'react-router-dom';
    import api from '../../api';
    import { 
        MapPin, Minimize2, Calendar, Thermometer, Droplets, Zap, Leaf, Droplet,
        Wind, FlaskConical, Layers, Activity, Sun 
    } from 'lucide-react';
    import { format } from 'date-fns';

    const Spinner = ({ size = 'md' }) => {
        const sizeClasses = {
            sm: 'w-6 h-6',
            md: 'w-10 h-10',
            lg: 'w-16 h-16',
        };
        return (
            <div className={`animate-spin rounded-full border-4 border-t-4 border-slate-200 border-t-emerald-600 ${sizeClasses[size]}`}></div>
        );
    };


    const FarmerDashboardPage = () => {
        const [farmInfo, setFarmInfo] = useState(null);
        const [iotData, setIotData] = useState(null);
        const [loading, setLoading] = useState(true);
        const [error, setError] = useState('');
        const [isAnalyzing, setIsAnalyzing] = useState(false);
        const navigate = useNavigate();

        useEffect(() => {
            const fetchDashboardData = async () => {
                try {
                    const [farmResponse, iotResponse] = await Promise.all([
                        api.get('/user/my-farm'),
                        api.get('/farm/iot-data')
                    ]);
                    setFarmInfo(farmResponse.data);
                    setIotData(iotResponse.data);
                } catch (err) {
                    setError("Không thể tải dữ liệu dashboard. Vui lòng thử lại sau.");
                    console.error(err);
                } finally {
                    setLoading(false);
                }
            };
            fetchDashboardData();
        }, []);

        const handleStartAnalysis = async () => {
            setIsAnalyzing(true);
            setError('');
            try {
                const response = await api.post('/treatment/analyze');
                navigate('/farmer/notifications', { state: { newNotification: response.data } });
            } catch (err) {
                setError(err.response?.data?.error || "Lỗi khi bắt đầu phân tích. Vui lòng thử lại.");
                console.error(err);
            } finally {
                setIsAnalyzing(false);
            }
        };

        if (loading) {
            return <div className="flex h-full items-center justify-center"><Spinner /></div>;
        }

        return (
            <div className="space-y-8 animate-fade-in">
                {farmInfo ? (
                    <>
                        <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200">
                            <h1 className="text-3xl font-bold text-slate-800">Chào mừng trở lại, {farmInfo.farmer_name}!</h1>
                            <p className="text-slate-600 mt-2">Đây là bảng điều khiển nông trại <strong className="text-emerald-700">{farmInfo.name}</strong> của bạn.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                            {/* Farm Info Cards */}
                            <InfoCard icon={<MapPin />} label="Tỉnh" value={farmInfo.province} />
                            <InfoCard icon={<Minimize2 />} label="Diện tích" value={`${farmInfo.area_ha} ha`} />
                            <InfoCard icon={<Calendar />} label="Ngày gieo sạ" value={farmInfo.planting_date ? format(new Date(farmInfo.planting_date), 'dd/MM/yyyy') : 'N/A'} />
                            
                            <InfoCard icon={<Thermometer />} label="Nhiệt độ" value={iotData ? `${iotData.temperature}°C` : 'N/A'} />
                            <InfoCard icon={<Wind />} label="Độ ẩm không khí" value={iotData ? `${iotData.humidity}%` : 'N/A'} />
                            <InfoCard icon={<Droplets />} label="Độ ẩm đất" value={iotData ? `${iotData.soil_moisture}%` : 'N/A'} />
                            <InfoCard icon={<FlaskConical />} label="Độ pH đất" value={iotData ? iotData.soil_ph : 'N/A'} />
                            <InfoCard icon={<Layers />} label="Mực nước" value={iotData ? `${iotData.water_level} cm` : 'N/A'} />
                        </div>

                        <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                            <h2 className="text-xl font-bold text-slate-800 mb-4">Hành động nhanh</h2>
                            {error && <p className="mb-4 text-sm text-red-600 bg-red-50 p-3 rounded-md">{error}</p>}
                            <div className="flex flex-wrap gap-4">
                                <button
                                    onClick={handleStartAnalysis}
                                    disabled={isAnalyzing}
                                    className="flex items-center justify-center gap-2 bg-emerald-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-slate-400 disabled:cursor-not-allowed cursor-pointer"
                                >
                                    {isAnalyzing ? <Spinner size="sm" /> : <Zap size={20} />}
                                    {isAnalyzing ? 'Đang phân tích...' : 'Bắt đầu Phân tích'}
                                </button>
                                <button onClick={() => navigate('/farmer/fertilizer-plan')} className="flex items-center justify-center gap-2 bg-emerald-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-slate-400 disabled:cursor-not-allowed cursor-pointer">
                                    <Leaf size={20} /> Kế hoạch Bón phân
                                </button>
                                <button onClick={() => navigate('/farmer/water-plan')} className="flex items-center justify-center gap-2 bg-emerald-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-slate-400 disabled:cursor-not-allowed cursor-pointer">
                                    <Droplet size={20} /> Kế hoạch Tưới tiêu
                                </button>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="text-center p-8 bg-yellow-50 text-yellow-700 rounded-lg">
                        Không có thông tin nông trại để hiển thị.
                    </div>
                )}
            </div>
        );
    };

    const InfoCard = ({ icon, label, value }) => (
        <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200 flex items-center gap-4">
            <div className="bg-emerald-100 text-emerald-600 p-3 rounded-full">{icon}</div>
            <div>
                <p className="text-sm text-slate-500">{label}</p>
                <p className="text-lg font-bold text-slate-800">{value}</p>
            </div>
        </div>
    );

    export default FarmerDashboardPage;

