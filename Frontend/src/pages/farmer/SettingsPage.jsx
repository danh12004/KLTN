import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';
import api from '../../api';

const Spinner = ({ size = 'md', color = 'emerald' }) => {
    const sizeClasses = {
        sm: 'w-4 h-4',
        md: 'w-8 h-8',
        lg: 'w-12 h-12',
    };
    const colorClasses = {
        emerald: 'border-emerald-500',
        white: 'border-white',
    };
    return (
        <div className={`animate-spin rounded-full border-t-2 border-r-2 ${sizeClasses[size]} ${colorClasses[color]}`} role="status">
            <span className="sr-only">Loading...</span>
        </div>
    );
};

const InputField = ({ label, ...props }) => (
    <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
        <input
            {...props}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-200 disabled:cursor-not-allowed"
        />
    </div>
);

const SelectField = ({ label, children, ...props }) => (
    <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
        <select
            {...props}
            className="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-slate-200 disabled:cursor-not-allowed"
        >
            {children}
        </select>
    </div>
);

const CustomToggleSwitch = ({ checked, onChange, disabled, name }) => (
    <label className="relative inline-flex items-center cursor-pointer">
        <input 
            type="checkbox" 
            name={name} 
            checked={checked} 
            onChange={onChange} 
            className="sr-only peer" 
            disabled={disabled} 
        />
        <div className="w-11 h-6 bg-slate-200 rounded-full peer peer-focus:ring-4 peer-focus:ring-emerald-300 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
        <span className="ml-3 text-sm font-medium text-slate-900">{checked ? "Đang bật" : "Đang tắt"}</span>
    </label>
);

const Notification = ({ message, type, onDismiss }) => {
    if (!message) return null;
    const isSuccess = type === 'success';
    const bgColor = isSuccess ? 'bg-green-100' : 'bg-red-100';
    const textColor = isSuccess ? 'text-green-800' : 'text-red-800';
    const Icon = isSuccess ? CheckCircle : AlertCircle;

    return (
        <div className={`${bgColor} ${textColor} p-4 rounded-lg flex items-center justify-between shadow-md mb-6 animate-fade-in`}>
            <div className="flex items-center">
                <Icon className="mr-3 flex-shrink-0" />
                <span>{message}</span>
            </div>
            <button onClick={onDismiss} className="text-lg font-bold ml-4">&times;</button>
        </div>
    );
};

const SettingsPage = () => {
    const [farmInfo, setFarmInfo] = useState({ 
        name: '', province: '', area_ha: '', planting_date: '',
        rice_variety: '', soil_type: ''
    });
    const [settings, setSettings] = useState({ enabled: false, interval: 24 });
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [notification, setNotification] = useState({ message: '', type: '' });
    
    const [originalFarmInfo, setOriginalFarmInfo] = useState({});
    const [originalSettings, setOriginalSettings] = useState({});

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [farmRes, settingsRes] = await Promise.all([
                    api.get('/user/my-farm'),
                    api.get('/user/settings')
                ]);
                
                const formattedFarmInfo = {
                    ...farmRes.data,
                    planting_date: farmRes.data.planting_date ? new Date(farmRes.data.planting_date).toISOString().split('T')[0] : '',
                    rice_variety: farmRes.data.rice_variety || '',
                    soil_type: farmRes.data.soil_type || ''
                };
                
                const formattedSettings = {
                    enabled: settingsRes.data.notification_enabled,
                    interval: settingsRes.data.notification_interval_hours
                };

                setFarmInfo(formattedFarmInfo);
                setSettings(formattedSettings);
                
                setOriginalFarmInfo(formattedFarmInfo);
                setOriginalSettings(formattedSettings);

            } catch (err) {
                console.error("Failed to fetch settings:", err);
                setNotification({ message: 'Không thể tải cài đặt. Vui lòng thử lại.', type: 'error' });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);
    
    const handleSave = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setNotification({ message: '', type: '' });

        const dataToSave = {
            farm_info: farmInfo,
            notification_settings: settings
        };

        try {
            await api.post('/user/settings', dataToSave);
            setNotification({ message: 'Cập nhật cài đặt thành công!', type: 'success' });
            
            const newOriginalSettings = { ...settings };
            const newOriginalFarmInfo = { ...farmInfo };
            setOriginalFarmInfo(newOriginalFarmInfo);
            setOriginalSettings(newOriginalSettings);

            setIsEditing(false);
        } catch (error) {
            console.error("Failed to save settings:", error);
            setNotification({ message: 'Lỗi! Không thể lưu thay đổi.', type: 'error' });
        } finally {
            setIsSaving(false);
        }
    };
    
    const handleCancel = () => {
        setFarmInfo(originalFarmInfo);
        setSettings(originalSettings);
        setIsEditing(false);
        setNotification({ message: '', type: '' });
    };

    const handleInputChange = (e) => {
        const { name, value, type } = e.target;
        setFarmInfo(prev => ({ ...prev, [name]: type === 'number' ? parseFloat(value) || '' : value }));
    };

    const handleSettingsChange = (e) => {
        const { name, value, checked, type } = e.target;
        setSettings(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : parseInt(value, 10) }));
    };

    if (loading) return <div className="flex h-full items-center justify-center"><Spinner /></div>;

    return (
        <div className="max-w-2xl mx-auto p-4 sm:p-6 bg-slate-50 min-h-screen">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Cài đặt</h1>
            <Notification message={notification.message} type={notification.type} onDismiss={() => setNotification({ message: '', type: '' })} />

            <form onSubmit={handleSave} className="space-y-8">
                <div className="bg-white p-6 sm:p-8 rounded-xl shadow-md border border-slate-200">
                    <h2 className="text-xl font-bold text-slate-700 mb-4">Thông tin Nông trại</h2>
                    <div className="space-y-6">
                        <InputField label="Tên nông trại" name="name" value={farmInfo.name || ''} onChange={handleInputChange} disabled={!isEditing} required/>
                        <InputField label="Tỉnh" name="province" value={farmInfo.province || ''} onChange={handleInputChange} disabled={!isEditing} required/>
                        <InputField label="Diện tích (ha)" name="area_ha" type="number" step="0.1" value={farmInfo.area_ha || ''} onChange={handleInputChange} disabled={!isEditing} required/>
                        <InputField label="Ngày gieo sạ" name="planting_date" type="date" value={farmInfo.planting_date || ''} onChange={handleInputChange} disabled={!isEditing} required/>
                        
                        <SelectField label="Giống lúa" name="rice_variety" value={farmInfo.rice_variety} onChange={handleInputChange} disabled={!isEditing} required>
                            <option value="" disabled>Chọn giống lúa</option>
                            <option value="OM5451">OM 5451</option>
                            <option value="OM18">OM 18</option>
                            <option value="DaiThom8">Đài Thơm 8</option>
                            <option value="ST25">ST25</option>
                            <option value="Jasmine85">Jasmine 85</option>
                            <option value="other">Giống khác</option>
                        </SelectField>

                        <SelectField label="Loại đất chính" name="soil_type" value={farmInfo.soil_type} onChange={handleInputChange} disabled={!isEditing} required>
                            <option value="" disabled>Chọn loại đất</option>
                            <option value="phu_sa">Đất phù sa</option>
                            <option value="phen">Đất phèn (chua)</option>
                            <option value="xam_bac_mau">Đất xám bạc màu</option>
                            <option value="man">Đất mặn</option>
                        </SelectField>
                    </div>
                </div>

                <div className="bg-white p-6 sm:p-8 rounded-xl shadow-md border border-slate-200">
                    <h2 className="text-xl font-bold text-slate-700 mb-4">Giám sát Tự động</h2>
                    <div className="space-y-6">
                        <CustomToggleSwitch checked={settings.enabled} name="enabled" onChange={handleSettingsChange} disabled={!isEditing} />
                        <SelectField label="Tần suất kiểm tra" name="interval" value={settings.interval} onChange={handleSettingsChange} disabled={!isEditing || !settings.enabled}>
                            <option value={1}>Mỗi 1 giờ</option>
                            <option value={4}>Mỗi 4 giờ</option>
                            <option value={8}>Mỗi 8 giờ</option>
                            <option value={12}>Mỗi 12 giờ</option>
                            <option value={24}>Mỗi 24 giờ</option>
                        </SelectField>
                    </div>
                </div>

                <div className="flex justify-end gap-4 pt-4">
                    {isEditing ? (
                        <>
                            <button type="button" onClick={handleCancel} disabled={isSaving} className="px-6 py-2 rounded-lg bg-slate-200 text-slate-800 font-semibold hover:bg-slate-300 disabled:opacity-50 transition-colors">Hủy</button>
                            <button type="submit" disabled={isSaving} className="px-6 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:bg-slate-400 flex items-center justify-center gap-2 transition-colors">
                                {isSaving ? <Spinner size="sm" color="white" /> : null}
                                {isSaving ? 'Đang lưu...' : 'Lưu thay đổi'}
                            </button>
                        </>
                    ) : (
                        <button type="button" onClick={() => setIsEditing(true)} className="px-6 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 transition-colors">Chỉnh sửa</button>
                    )}
                </div>
            </form>
        </div>
    );
};

export default SettingsPage;

