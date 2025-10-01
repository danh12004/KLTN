import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import api from '../../api';
import Spinner from '../../components/Spinner';
import { MapPin, Minimize2, Calendar, Wind, Thermometer, Droplets } from 'lucide-react';
import { format } from 'date-fns';

const FarmerDashboardPage = () => {
    const [farmInfo, setFarmInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchFarmInfo = async () => {
            try {
                const response = await api.get('/my-farm');
                setFarmInfo(response.data);
            } catch (err) {
                setError("Không thể tải thông tin nông trại. Vui lòng thử lại sau.");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchFarmInfo();
    }, []);

    if (loading) {
        return <div className="flex h-full items-center justify-center"><Spinner /></div>;
    }

    if (error) {
        return <div className="text-center p-8 bg-red-50 text-red-700 rounded-lg">{error}</div>;
    }

    return (
        <div className="space-y-8 animate-fade-in">
            {farmInfo ? (
                <>
                    <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200">
                        <h1 className="text-3xl font-bold text-slate-800">Chào mừng trở lại, {farmInfo.farmer_name}!</h1>
                        <p className="text-slate-600 mt-2">Đây là bảng điều khiển nông trại <strong className="text-emerald-700">{farmInfo.name}</strong> của bạn.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <InfoCard icon={<MapPin />} label="Tỉnh" value={farmInfo.province} />
                        <InfoCard icon={<Minimize2 />} label="Diện tích" value={`${farmInfo.area_ha} ha`} />
                        <InfoCard icon={<Calendar />} label="Ngày gieo sạ" value={farmInfo.planting_date ? format(new Date(farmInfo.planting_date), 'dd/MM/yyyy') : 'Chưa có'} />
                        <InfoCard icon={<Thermometer />} label="Nhiệt độ" value="32°C" />
                    </div>
                </>
            ) : (
                <div className="text-center p-8 bg-yellow-50 text-yellow-700 rounded-lg">
                    Không có thông tin nông trại để hiển thị. Vui lòng cập nhật thông tin trong phần Cài đặt.
                </div>
            )}
        </div>
    );
};

const InfoCard = ({ icon, label, value }) => (
    <div className="bg-white p-6 rounded-xl shadow-md border border-slate-200 flex items-center gap-4">
        <div className="bg-emerald-100 text-emerald-600 p-3 rounded-full">
            {icon}
        </div>
        <div>
            <p className="text-sm text-slate-500">{label}</p>
            <p className="text-lg font-bold text-slate-800">{value}</p>
        </div>
    </div>
);

export default FarmerDashboardPage;