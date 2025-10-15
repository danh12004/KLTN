import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { BellOff, CheckCircle, Send, Zap } from 'lucide-react';
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


const ConversationView = ({ planData, planChatHistory, onUpdatePlan, onExecute, isSending, isExecuting }) => {
    const [userInput, setUserInput] = useState('');
    const chatEndRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [planChatHistory]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (userInput.trim() && !isSending) {
            onUpdatePlan(userInput);
            setUserInput('');
        }
    };

    return (
        <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-200px)]">
            {/* --- Chi tiết Kế hoạch (Trái) --- */}
            <div className="w-full lg:w-1/2 bg-white rounded-lg shadow-md border border-slate-200 p-6 overflow-y-auto">
                <h2 className="text-xl font-bold text-slate-800 mb-4">Chi tiết Kế hoạch</h2>
                <div className="space-y-4 text-slate-700">
                    <p><strong>Đánh giá rủi ro:</strong> {planData.analysis.risk_assessment}</p>
                    <p><strong>Tóm tắt thời tiết:</strong> {planData.analysis.weather_summary}</p>
                    <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                        <p><strong>Thuốc đề xuất:</strong> {planData.treatment_plan.drug_info.sản_phẩm_tham_khảo}</p>
                        <p><strong>Liều lượng:</strong> {planData.treatment_plan.drug_info.liều_lượng}</p>
                        <p><strong>Thời điểm phun:</strong> {planData.treatment_plan.optimal_spray_day.date} (Buổi {planData.treatment_plan.optimal_spray_day.session})</p>
                    </div>
                    <p><strong>Hành động bổ sung:</strong> {planData.treatment_plan.additional_actions.join(', ')}</p>
                    <p><strong>Tư vấn bón phân:</strong> {planData.fertilizer_advice.recommendation}</p>
                    <p><strong>Dự báo:</strong> {planData.prognosis}</p>
                </div>
            </div>

            {/* --- Khung Chat (Phải) --- */}
            <div className="w-full lg:w-1/2 bg-white rounded-lg shadow-md border border-slate-200 flex flex-col p-4">
                <div className="flex-grow overflow-y-auto pr-2 space-y-4 mb-4">
                    {planChatHistory.map((msg, index) => (
                        <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-xs md:max-w-md p-3 rounded-lg ${msg.sender === 'user' ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-800'}`}>
                                {msg.text}
                            </div>
                        </div>
                    ))}
                    <div ref={chatEndRef} />
                </div>
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <input
                        type="text"
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        placeholder="Nhập yêu cầu điều chỉnh..."
                        className="flex-grow px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        disabled={isSending}
                    />
                    <button type="submit" className="bg-emerald-600 text-white p-2 rounded-lg hover:bg-emerald-700 disabled:bg-slate-400" disabled={isSending}>
                        <Send size={20} />
                    </button>
                </form>
                <button 
                    onClick={onExecute} 
                    disabled={isExecuting}
                    className="w-full mt-4 bg-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-slate-400 flex items-center justify-center gap-2"
                >
                    {isExecuting ? <Spinner size="sm" color="white"/> : <Zap size={20} />}
                    {isExecuting ? 'Đang gửi...' : 'Xác nhận & Thực thi Kế hoạch'}
                </button>
            </div>
        </div>
    );
};

const NotificationPage = () => {
    const [sessionId, setSessionId] = useState(null);
    const [plan, setPlan] = useState(null);
    const [chatHistory, setChatHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [isExecuting, setIsExecuting] = useState(false);
    const [executionSuccess, setExecutionSuccess] = useState(false);

    const location = useLocation();
    const navigate = useNavigate();
    
    const sessionIdRef = useRef(null);
    useEffect(() => {
        sessionIdRef.current = sessionId;
    }, [sessionId]);

    useEffect(() => {
        let pollInterval;

        const loadNotification = async () => {
            try {
                const response = await api.get('/user/notifications/latest');
                if (response.data.conversation_id !== sessionIdRef.current) {
                    console.log("Polling found a new notification!", response.data.conversation_id);
                    initializePlan(response.data);
                    setError('');
                    setExecutionSuccess(false); 
                }
            } catch (err) {
                if (err.response && err.response.status === 404) {
                    if (!sessionIdRef.current) {
                       setError("Hiện tại không có thông báo hay cảnh báo mới nào.");
                    }
                } else {
                    setError("Không thể tải thông báo. Vui lòng thử lại.");
                    console.error(err);
                }
            } finally {
                if (loading) setLoading(false);
            }
        };

        if (location.state?.newNotification) {
            console.log("Initializing with data from navigation state.");
            initializePlan(location.state.newNotification);
            setLoading(false);
            navigate(location.pathname, { replace: true, state: {} });
        } else {
            console.log("No navigation state, fetching latest notification.");
            loadNotification();
        }
        pollInterval = setInterval(loadNotification, 15000);

        return () => clearInterval(pollInterval);
        
    }, []); 

    const initializePlan = (data) => {
        const { conversation_id, plan: initialPlan } = data;
        if (!initialPlan) {
            setError("Dữ liệu thông báo không hợp lệ.");
            setLoading(false);
            return;
        }
        setSessionId(conversation_id);
        setPlan(initialPlan);

        const mainMessage = initialPlan?.treatment_plan?.main_message || "Đây là kết quả phân tích tự động.";
        setChatHistory([
            { sender: 'ai', text: mainMessage },
            { sender: 'ai', text: "Bạn có muốn điều chỉnh gì trong kế hoạch này không?" }
        ]);
    };
    
    const handleUpdatePlan = async (message) => {
        setIsSending(true);
        setChatHistory(prev => [...prev, { sender: 'user', text: message }]);

        try {
            const response = await api.post('/treatment/chat', { conversation_id: sessionId, message, plan });
            const updatedPlan = response.data.plan;
            setPlan(updatedPlan);
            setChatHistory(prev => [...prev, { sender: 'ai', text: updatedPlan.treatment_plan.main_message }]);
        } catch (err) {
            const errorMsg = "Xin lỗi, tôi chưa thể xử lý yêu cầu này.";
            setChatHistory(prev => [...prev, { sender: 'ai', text: errorMsg }]);
        } finally {
            setIsSending(false);
        }
    };
    
    const handleExecutePlan = async () => {
        setIsExecuting(true);
        try {
            await api.post('/treatment/execute', { conversation_id: sessionId });
            setExecutionSuccess(true);
        } catch (err) {
            setError(err.response?.data?.error || "Lỗi khi thực thi kế hoạch.");
        } finally {
            setIsExecuting(false);
        }
    };

    const renderContent = () => {
        if (loading) return <div className="flex justify-center py-10"><Spinner /></div>;

        if (executionSuccess) {
            return (
                <div className="text-center p-10 bg-white rounded-lg shadow-md border border-green-200">
                    <CheckCircle size={48} className="mx-auto text-green-500" />
                    <h2 className="mt-4 text-xl font-semibold text-slate-700">Thực thi thành công!</h2>
                    <p className="text-slate-500 mt-2">Kế hoạch đã được xác nhận và gửi đi.</p>
                    <button onClick={() => navigate('/farmer/dashboard')} className="mt-6 bg-emerald-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-emerald-700">
                        Quay về Bảng điều khiển
                    </button>
                </div>
            );
        }
        
        if (error && !plan) {
            return (
                <div className="text-center p-10 bg-white rounded-lg shadow-md">
                    <BellOff size={48} className="mx-auto text-slate-400" />
                    <p className="text-slate-600 mt-4">{error}</p>
                </div>
            );
        }

        if (plan) {
            return (
                <ConversationView
                    planData={plan}
                    planChatHistory={chatHistory}
                    onUpdatePlan={handleUpdatePlan}
                    onExecute={handleExecutePlan}
                    isSending={isSending}
                    isExecuting={isExecuting}
                />
            );
        }
        
        return <div className="flex justify-center py-10"><Spinner /></div>; 
    };

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Thông Báo & Điều Trị</h1>
            {renderContent()}
        </div>
    );
};

export default NotificationPage;
