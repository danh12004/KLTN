import React, { useState, useEffect } from 'react';
import { ToggleSwitch } from 'flowbite-react';
import Spinner from '../../components/Spinner';
import { useSettings } from '../../context/SettingsContext';
import api from '../../api';

const InputField = ({ label, ...props }) => (
    <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
        <input
            {...props}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-200 disabled:cursor-not-allowed"
        />
    </div>
);

const SelectField = ({ label, value, onChange, name, disabled, children }) => (
    <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
        <select
            name={name}
            value={value}
            onChange={onChange}
            disabled={disabled}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-200 disabled:cursor-not-allowed"
        >
            {children}
        </select>
    </div>
);

const SettingsPage = () => {
    const { settings, saveSettings, isPolling, togglePolling, loadingSettings } = useSettings();

    const [farmInfo, setFarmInfo] = useState({ name: '', province: '', area_ha: '', planting_date: '' });
    const [localInterval, setLocalInterval] = useState(settings.interval);
    
    const [loadingFarm, setLoadingFarm] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    
    useEffect(() => {
        const fetchFarm = async () => {
            try {
                const farmRes = await api.get('/my-farm');
                setFarmInfo(farmRes.data);
            } catch (err) {
                console.error("Không thể tải thông tin nông trại", err);
            } finally {
                setLoadingFarm(false);
            }
        };
        fetchFarm();
    }, []);
    
    useEffect(() => {
        setLocalInterval(settings.interval);
    }, [settings.interval]);

    const handleSave = async (e) => {
        e.preventDefault();
        
        const notificationSettingsToSave = { 
            enabled: isPolling, 
            interval: localInterval 
        };
        
        const dataToSave = {
            farm_info: farmInfo,
            notification_settings: notificationSettingsToSave
        };

        try {
            await api.post('/settings', dataToSave);
            saveSettings(notificationSettingsToSave);
            alert("Lưu thông tin thành công!");
            setIsEditing(false);
        } catch (error) {
            alert("Lỗi! Không thể lưu thông tin.");
            console.error("Lỗi khi lưu cài đặt và thông tin nông trại", error);
        }
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFarmInfo(prev => ({ ...prev, [name]: value }));
    };

    const handleCancel = () => {
        setLocalInterval(settings.interval); 
        setIsEditing(false);
    };

    if (loadingSettings || loadingFarm) return <Spinner />;

    return (
        <div className="animate-fade-in max-w-2xl mx-auto">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Cài đặt</h1>
            <form onSubmit={handleSave} className="space-y-8">
                <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200">
                    <h2 className="text-xl font-bold text-slate-700 mb-4">Thông tin Nông trại</h2>
                    <div className="space-y-6">
                        <InputField label="Tên nông trại" name="name" value={farmInfo.name || ''} onChange={handleInputChange} disabled={!isEditing} />
                        <InputField label="Tỉnh" name="province" value={farmInfo.province || ''} onChange={handleInputChange} disabled={!isEditing} />
                        <InputField label="Diện tích (ha)" name="area_ha" type="number" value={farmInfo.area_ha || ''} onChange={handleInputChange} disabled={!isEditing} />
                        <InputField label="Ngày gieo sạ" name="planting_date" type="date" value={farmInfo.planting_date || ''} onChange={handleInputChange} disabled={!isEditing} />
                    </div>
                </div>

                <div className="bg-white p-8 rounded-xl shadow-md border border-slate-200">
                    <h2 className="text-xl font-bold text-slate-700 mb-4">Giám sát Tự động</h2>
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Bắt đầu/Dừng Giám sát
                            </label>
                            <ToggleSwitch
                                checked={isPolling}
                                onChange={togglePolling} 
                                label={isPolling ? "Đang chạy" : "Đang dừng"}
                            />
                            <p className="text-xs text-slate-500 mt-1">
                                {isPolling 
                                    ? `Hệ thống đang tự động kiểm tra mỗi ${settings.interval} giờ.`
                                    : 'Bật để bắt đầu nhận cảnh báo tự động.'}
                            </p>
                        </div>
                        <SelectField
                            label="Tần suất kiểm tra"
                            name="interval"
                            value={localInterval}
                            onChange={(e) => setLocalInterval(parseInt(e.target.value, 10))}
                            disabled={!isEditing}
                        >
                            <option value={1}>Mỗi 1 giờ</option>
                            <option value={4}>Mỗi 4 giờ</option>
                            <option value={8}>Mỗi 8 giờ</option>
                            <option value={12}>Mỗi 12 giờ</option>
                            <option value={24}>Mỗi 24 giờ (1 ngày)</option>
                        </SelectField>
                    </div>
                </div>

                <div className="flex justify-end gap-4 pt-4">
                    {isEditing ? (
                        <>
                            <button type="button" onClick={handleCancel} className="px-6 py-2 rounded-lg bg-slate-200 text-slate-800 hover:bg-slate-300">Hủy</button>
                            <button type="submit" className="px-6 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700">Lưu thay đổi</button>
                        </>
                    ) : (
                        <button type="button" onClick={() => setIsEditing(true)} className="px-6 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700">Chỉnh sửa</button>
                    )}
                </div>
            </form>
        </div>
    );
};

export default SettingsPage;