import React, { useState, useEffect, useMemo } from 'react';
import { initializeApp } from "firebase/app";
import { getDatabase, ref, onValue } from "firebase/database";
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import { 
    MapPin, Minimize2, Calendar, Zap, Leaf, Droplet, TrendingUp, Map, Thermometer, Wind
} from 'lucide-react';
import { format } from 'date-fns';

import { 
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, ReferenceArea 
} from 'recharts';

import { MapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet'; 
import L from 'leaflet';

const firebaseConfig = {
  apiKey: "AIzaSyDim913yfY20GhBh_ytw7hTCyYR5tCLWCA",
  authDomain: "rice-813b5.firebaseapp.com",
  databaseURL: "https://rice-813b5-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "rice-813b5",
  storageBucket: "rice-813b5.firebasestorage.app",
  messagingSenderId: "764360487023",
  appId: "1:764360487023:web:9ed5997918a97057a09d9a",
  measurementId: "G-4BYCXYVPFT"
};

const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

if (L && L.Icon && L.Icon.Default) {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });
}

const ICON_COLORS = {
    'Giám sát/Xử lý': '#E53E3E',
    'Quản lý nước': '#3182CE',    
    'Bón phân': '#38A169',       
    'Không rõ': '#718096',       
};

const createCustomIcon = (color) => {
    return L.divIcon({ 
        className: 'custom-map-icon',
        html: `<div style="background-color: ${color}; width: 15px; height: 15px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.7);"></div>`, 
        iconSize: [21, 21],
        iconAnchor: [10, 10],
    });
};

const ChangeView = ({ center, zoom }) => {
    try {
        const map = useMap();
        map.setView(center, zoom);
    } catch (e) {
        console.warn("ChangeView: useMap hook not available outside MapContainer context.");
    }
    return null;
}

const CHART_POLLING_INTERVAL = 300000; 

const Spinner = ({ size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-6 h-6',
        md: 'w-10 h-10',
        lg: 'w-16 h-16',
    };
    return (
        <div className={`animate-spin rounded-full border-4 border-slate-200 border-t-emerald-600 ${sizeClasses[size]}`}></div>
    );
};

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        const dataPoint = payload[0].payload;
        const isForecast = dataPoint.is_forecast;

        return (
            <div className="bg-white p-3 border border-slate-300 shadow-lg text-sm rounded-md">
                <p
                    className={`font-bold ${isForecast ? 'text-emerald-700' : 'text-slate-800'}`}
                >
                    {isForecast ? "Dự báo" : "Lịch sử"} - {format(new Date(label), 'HH:mm dd/MM')}
                </p>

                {payload.map((p, index) => {
                    let decimalPlaces = 1; 
                    if (p.name.includes('pH')) {
                        decimalPlaces = 2; 
                    } else if (p.name.includes('nước') || p.name.includes('Gió')) {
                        decimalPlaces = 1; 
                    }

                    const displayValue =
                        p.value !== undefined && p.value !== null
                            ? parseFloat(p.value).toFixed(decimalPlaces)
                            : 'N/A';

                    const unit =
                        p.name.includes('Nhiệt độ') ? '°C' :
                        p.name.includes('ẩm') || p.name.includes('đất') ? '%' :
                        p.name.includes('nước') ? ' cm' :
                        p.name.includes('Gió') ? ' m/s' : ''; 

                    return (
                        <p key={index} style={{ color: p.color }}>
                            {p.name}: <span className="font-semibold">{displayValue}{unit}</span>
                        </p>
                    );
                })}
            </div>
        );
    }
    return null;
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

const FarmerDashboardPage = () => {
    const [farmInfo, setFarmInfo] = useState(null);
    const [realTimeData, setRealTimeData] = useState(null);
    const [loadingInitial, setLoadingInitial] = useState(true);

    const [chartDataState, setChartDataState] = useState(null);
    const [loadingChart, setLoadingChart] = useState(true);

    const [error, setError] = useState('');
    
    const defaultCenter = useMemo(() => ({ lat: 10.77, lon: 106.69 }), []);
    const [analysisLocations, setAnalysisLocations] = useState([]);
    const [mapCenter, setMapCenter] = useState(defaultCenter);
    const initialZoom = 15;

    const navigate = useNavigate();

    const fetchFarmInfo = async () => {
        try {
            const response = await api.get('/user/farm-info-and-realtime'); 
            setFarmInfo(response.data.farm_info); 
        } catch (err) {
            setError(err.response?.data?.error || "Không thể tải thông tin nông trại ban đầu.");
            console.error("Lỗi tải farm info:", err);
        } finally {
            setLoadingInitial(false); 
        }
    };
    
    const fetchChartAndForecastData = async () => {
        setLoadingChart(true); 
        try {
            const response = await api.get('/user/chart-and-forecast-data'); 

            const processedChartData = response.data.chart_data.map(d => ({
                ...d,
                date: new Date(d.date).getTime(), 
            }));

            const sortedChartData = processedChartData.sort(
                (a, b) => a.date - b.date
            );

            const forecastStartDateTimestamp = response.data.forecast_start_date 
                                             ? new Date(response.data.forecast_start_date).getTime() 
                                             : null;

            setChartDataState({
                chart_data: sortedChartData,
                forecast_start_date: forecastStartDateTimestamp 
            });

        } catch (err) {
            console.error("Lỗi tải biểu đồ/dự báo:", err);
        } finally {
            setLoadingChart(false); 
        }
    };

    const fetchAnalysisLocations = async () => {
        try {
            const response = await api.get('/user/all-analysis-locations');
            const locs = response.data.map(loc => ({
                ...loc,
                link: `/farmer/analysis/${loc.id}` 
            }));
            setAnalysisLocations(locs);

            if (locs.length > 0) {
                const latestLoc = locs.find(loc => loc.lat && loc.lon); 
                if (latestLoc) {
                    setMapCenter({ lat: latestLoc.lat, lon: latestLoc.lon });
                }
            }
        } catch (err) {
            console.error("Lỗi khi tải lịch sử phân tích:", err);
        }
    }

    useEffect(() => {
        fetchFarmInfo();
        
        const feedsRef = ref(database, 'feeds');
        
        const unsubscribe = onValue(feedsRef, (snapshot) => {
            const allFeeds = snapshot.val();
            if (allFeeds) {
                const latestDateKey = Object.keys(allFeeds).sort().reverse()[0];
                const latestDateEntry = allFeeds[latestDateKey];
                
                if (latestDateEntry) {
                    const latestTimestampKey = Object.keys(latestDateEntry).sort().reverse()[0];
                    const latestEntry = latestDateEntry[latestTimestampKey];
                    
                    if (latestEntry && latestEntry.env) {
                        const env_data = latestEntry.env;
                        const mappedData = {
                            timestamp: env_data.time || latestTimestampKey,
                            temperature: env_data.temp,
                            humidity: env_data.hum,
                            soil_moisture: env_data.soil,
                            soil_ph: env_data.ph,
                            lux: env_data.lux,
                            wind: env_data.wind,
                            wind_avg: env_data.wind_avg,
                            water_level: latestEntry.water_level || (Math.random() * 8 + 2).toFixed(1), 
                        };
                        setRealTimeData(mappedData);
                    }
                }
            } else {
                setRealTimeData(null);
            }
        }, (error) => {
            console.error("Lỗi khi lắng nghe Firebase:", error);
        });

        fetchAnalysisLocations(); 
        fetchChartAndForecastData();

        const chartIntervalId = setInterval(fetchChartAndForecastData, CHART_POLLING_INTERVAL);

        return () => {
            unsubscribe(); 
            clearInterval(chartIntervalId);
        };
    }, []);

    const AnalysisMapComponent = ({ center, zoom, markers }) => {
        if (!MapContainer || !L) return null;
        
        const currentCenter = [mapCenter.lat, mapCenter.lon];

        return (
            <div className="rounded-xl overflow-hidden shadow-xl border border-slate-200 h-[450px]">
                <MapContainer 
                    center={currentCenter} 
                    zoom={zoom} 
                    scrollWheelZoom={true} 
                    className="h-full w-full"
                    key={`map-${mapCenter.lat}-${mapCenter.lon}`}
                >
                    <ChangeView center={currentCenter} zoom={zoom} />
                    <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    
                    {markers.map((loc) => (
                        <Marker 
                            key={loc.id}
                            position={[loc.lat, loc.lon]}
                            icon={createCustomIcon(ICON_COLORS[loc.type] || ICON_COLORS['Không rõ'])}
                        >
                            <Tooltip 
                                direction="top"
                                offset={[0, -10]} 
                                opacity={1}
                            >
                                <div className="font-sans text-sm p-1">
                                    <strong className="text-base text-slate-800 block mb-1">{loc.type} (ID: {loc.id})</strong>
                                    <span style={{ color: ICON_COLORS[loc.type] || ICON_COLORS['Không rõ'] }} className="block font-bold">
                                        {loc.diagnosis}
                                    </span>
                                    <span className="block mt-1">
                                        Ngày: {format(new Date(loc.date), 'dd/MM/yyyy HH:mm')}
                                    </span>
                                    <span>
                                        Trạng thái: <span className="font-semibold">{loc.status}</span>
                                    </span>
                                </div>
                            </Tooltip>
                        </Marker>
                    ))}
                </MapContainer>
            </div>
        );
    };

    if (loadingInitial) {
        return <div className="flex h-full items-center justify-center"><Spinner /></div>;
    }
    
    const chartData = chartDataState?.chart_data || [];
    const forecastStartDate = chartDataState?.forecast_start_date;
    
    const lastHistoryEntry = chartData.slice().reverse().find(d => !d.is_forecast);


    const DashboardChart = ({ data, dataKey, name, color, isLoading }) => {
        
        return (
            <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200 h-96 flex flex-col">
                <h3 className="text-lg font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <TrendingUp size={20} className="text-emerald-600"/> {name} (Lịch sử & Dự báo 3 Ngày)
                </h3>
                {isLoading ? (
                    <div className="flex-grow flex items-center justify-center">
                        <Spinner size="lg" />
                    </div>
                ) : data.length === 0 ? (
                    <div className="flex-grow flex items-center justify-center text-slate-500">
                        Không có dữ liệu biểu đồ để hiển thị.
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="85%">
                        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis 
                                dataKey="date" 
                                scale="time" 
                                type="number"
                                domain={['auto', 'auto']}
                                tickFormatter={(tick) => {
                                    const date = new Date(tick);
                                    if (date.getHours() === 12) {
                                        return format(date, 'dd/MM'); 
                                    }
                                    return format(date, 'HH:mm dd/MM'); 
                                }}
                                interval="preserveStartEnd"
                                minTickGap={20}
                            />
                            <YAxis />
                            <RechartsTooltip content={<CustomTooltip />} />
                            <Legend />
                            
                            {lastHistoryEntry && forecastStartDate && (
                                <ReferenceArea 
                                    x1={lastHistoryEntry.date} 
                                    x2={data[data.length - 1].date} 
                                    fill="#e6ffed" 
                                    strokeOpacity={0.3}
                                    label={{ value: 'Vùng Dự báo', position: 'top', fill: '#059669', fontSize: 12, dx: 10 }}
                                />
                            )}

                            <Line 
                                type="monotone" 
                                dataKey={dataKey} 
                                name={name} 
                                stroke={color} 
                                strokeWidth={2}
                                dot={false}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>
        );
    };


    return (
        <div className="space-y-8 animate-fade-in">
            {farmInfo ? (
                <>
                    <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200">
                        <h1 className="text-3xl font-bold text-slate-800">Chào mừng trở lại, {farmInfo.farmer_name}!</h1>
                        <p className="text-slate-600 mt-2">Bảng điều khiển nông trại <strong className="text-emerald-700">{farmInfo.name}</strong> 
                            {/* {realTimeData && <span className="ml-4 text-sm text-slate-500">(Dữ liệu gần nhất: {format(new Date(realTimeData.timestamp), 'HH:mm dd/MM/yyyy')})</span>} */}
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                        <InfoCard icon={<MapPin />} label="Tỉnh" value={farmInfo.province} />
                        <InfoCard icon={<Minimize2 />} label="Diện tích" value={`${farmInfo.area_ha} ha`} />
                        <InfoCard icon={<Calendar />} label="Ngày gieo sạ" value={farmInfo.planting_date ? format(new Date(farmInfo.planting_date), 'dd/MM/yyyy') : 'N/A'} />
                        
                        <InfoCard icon={<Thermometer />} label="Nhiệt độ hiện tại" value={realTimeData?.temperature ? `${parseFloat(realTimeData.temperature).toFixed(1)}°C` : 'N/A'} />
                        <InfoCard icon={<Wind />} label="Độ ẩm hiện tại" value={realTimeData?.humidity ? `${parseFloat(realTimeData.humidity).toFixed(1)}%` : 'N/A'} />
                    </div>
                    
                    <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                        <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                            <Map size={24} className="text-emerald-600"/> Lịch Sử Vị Trí Phân Tích
                        </h2>
                        {analysisLocations.length > 0 ? (
                            <AnalysisMapComponent 
                                center={mapCenter} 
                                zoom={initialZoom} 
                                markers={analysisLocations} 
                            />
                        ) : (
                            <div className="p-4 bg-yellow-50 text-yellow-700 rounded-lg">Không có lịch sử phân tích GPS.</div>
                        )}
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                        <DashboardChart data={chartData} dataKey="temperature" name="Nhiệt độ" color="#ff6961" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="soil_moisture" name="Độ ẩm đất" color="#a8e6cf" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="humidity" name="Độ ẩm KK" color="#3399ff" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="water_level" name="Mực nước" color="#4287f5" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="lux" name="Cường độ ánh sáng" color="#fec84e" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="soil_ph" name="Độ pH đất" color="#9e66d4" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="wind" name="Tốc độ Gió" color="#808080" isLoading={loadingChart} />
                        <DashboardChart data={chartData} dataKey="wind_avg" name="Gió TB" color="#4682B4" isLoading={loadingChart} />
                    </div>
                    
                    <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200">
                        <h2 className="text-xl font-bold text-slate-800 mb-4">Hành động</h2>
                        {error && <p className="mb-4 text-sm text-red-600 bg-red-50 p-3 rounded-md">{error}</p>}
                        <div className="flex flex-wrap gap-4">
                            <button
                                onClick={() => navigate('/farmer/treatment')} 
                                className="flex items-center justify-center gap-2 bg-emerald-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-emerald-700 transition-colors disabled:bg-slate-400 disabled:cursor-not-allowed cursor-pointer"
                            >
                                <Zap size={20} /> Kế hoạch Giám sát/Xử lý
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

export default FarmerDashboardPage;