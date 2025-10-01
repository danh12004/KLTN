import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api from '../api';
import { useAuth } from './AuthContext';

const SettingsContext = createContext();

export const useSettings = () => useContext(SettingsContext);

export const SettingsProvider = ({ children }) => {
    const { user } = useAuth();
    const [settings, setSettings] = useState({ enabled: false, interval: 4 });
    const [isPolling, setIsPolling] = useState(false);
    const [latestNotification, setLatestNotification] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);

    const intervalRef = useRef(null);

    const fetchLatestData = useCallback(async () => {
        if (!user?.id) return;
        console.log("Đang tìm nạp thông báo mới...");
        setError(''); 
        try {
            const response = await api.post('/automated-analysis', { farmer_id: user.id });
            setLatestNotification(response.data);
        } catch (err) {
            const errorMessage = err.response?.data?.error || "Không thể lấy dữ liệu giám sát.";
            setError(errorMessage);
            setLatestNotification(null); 
        }
    }, [user]);

    useEffect(() => {
        const loadInitialSettings = async () => {
            if (user) {
                try {
                    setLoading(true);
                    const res = await api.get('/settings');
                    setSettings(res.data);
                } catch (e) {
                    console.error("Lỗi khi tải cài đặt", e);
                } finally {
                    setLoading(false);
                }
            }
        };
        loadInitialSettings();
    }, [user]);

    useEffect(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
        }

        if (isPolling && user) {
            fetchLatestData(); 
            
            const intervalInMs = settings.interval * 60 * 60 * 1000;
            intervalRef.current = setInterval(fetchLatestData, intervalInMs);
        }

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [isPolling, settings.interval, user, fetchLatestData]);

    const saveSettings = async (newSettings) => {
        try {
            await api.post('/settings', { notification_settings: newSettings });
            setSettings(newSettings);
        } catch (error) {
            console.error(error);
            throw error; 
        }
    };
    
    const togglePolling = (shouldPoll) => {
        setIsPolling(shouldPoll);
    };

    const value = {
        settings,
        saveSettings,
        isPolling,
        togglePolling,
        latestNotification,
        error,
        loadingSettings: loading
    };

    return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};