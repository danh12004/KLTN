import React, { useState, useEffect } from 'react';
import api from '../../api';
import Spinner from '../../components/Spinner';
import ConversationView from '../../components/ConversationView';
import { BellOff, AlertTriangle } from 'lucide-react';
import { useSettings } from '../../context/SettingsContext'; 

const NotificationPage = () => {
    const { latestNotification, error, isPolling } = useSettings();

    const [sessionId, setSessionId] = useState(null);
    const [plan, setPlan] = useState(null);
    const [planChatHistory, setPlanChatHistory] = useState([]);
    const [qaChatHistory, setQaChatHistory] = useState([]);
    const [isSendingMessage, setIsSendingMessage] = useState(false);
    const [isExecuting, setIsExecuting] = useState(false);

    useEffect(() => {
        if (latestNotification) {
            handleAnalysisSuccess(latestNotification);
        }
    }, [latestNotification]);

    const handleAnalysisSuccess = (data) => {
        const { conversation_id, plan: initialPlan } = data;
        setSessionId(conversation_id);
        setPlan(initialPlan);
        const mainMessage = initialPlan?.treatment_plan?.main_message || "Đây là kết quả phân tích tự động.";
        
        setPlanChatHistory([
            { sender: 'ai', text: "Kết quả giám sát tự động mới nhất:" },
            { sender: 'ai', text: mainMessage },
            { sender: 'ai', text: "Bác xem và cho tôi biết nếu có muốn thay đổi gì không ạ?" }
        ]);
        setQaChatHistory([{ sender: 'ai', text: "Chào bác, bác có câu hỏi gì về nông hộ của mình không ạ?" }]);
    };

    const handleUpdatePlan = async (message) => {
        setIsSendingMessage(true);
        setPlanChatHistory(prev => [...prev, { sender: 'user', text: message }]);

        try {
            const response = await api.post('/chat', { conversation_id: sessionId, message });
            const updatedPlan = response.data.plan;
            setPlan(updatedPlan);
            setPlanChatHistory(prev => [...prev, { sender: 'ai', text: updatedPlan.treatment_plan.main_message }]);
        } catch (err) {
            const errorMsg = "Xin lỗi, tôi chưa thể xử lý yêu cầu này.";
            setPlanChatHistory(prev => [...prev, { sender: 'ai', text: errorMsg }]);
        } finally {
            setIsSendingMessage(false);
        }
    };

    const handleAskQuestion = async (question) => {
        setIsSendingMessage(true);
        setQaChatHistory(prev => [...prev, { sender: 'user', text: question }]);
        
        try {
            const farmerId = plan?.analysis?.farmer_id;
            if (!farmerId) throw new Error("Missing farmer_id");

            const response = await api.post('/ask', { farmer_id: farmerId, question });
            setQaChatHistory(prev => [...prev, { sender: 'ai', text: response.data.answer }]);
        } catch (err) {
            const errorMsg = "Xin lỗi, tôi không thể trả lời câu hỏi này ngay bây giờ.";
            setQaChatHistory(prev => [...prev, { sender: 'ai', text: errorMsg }]);
        } finally {
            setIsSendingMessage(false);
        }
    };
    
    const handleExecutePlan = async () => {
        setIsExecuting(true);
        try {
            await api.post('/execute', { conversation_id: sessionId });
            alert("Kế hoạch đã được xác nhận và gửi đi thành công!");
            setView('no-notification');
            setError("Bạn đã xử lý xong thông báo. Hiện không còn thông báo mới.");
        } catch (err) {
            alert(err.response?.data?.error || "Lỗi khi thực thi kế hoạch.");
        } finally {
            setIsExecuting(false);
        }
    };
    
    const renderContent = () => {
        if (!isPolling && !latestNotification) {
            return (
                <div className="text-center p-10 bg-white rounded-lg shadow-md">
                    <BellOff size={48} className="mx-auto text-slate-400" />
                    <h2 className="mt-4 text-xl font-semibold text-slate-700">Chức năng giám sát đang tắt</h2>
                    <p className="text-slate-500 mt-2">Vui lòng vào trang "Cài đặt" để bắt đầu giám sát.</p>
                </div>
            );
        }

        if (error && !latestNotification) {
             return (
                <div className="text-center p-10 bg-amber-50 rounded-lg shadow-md border border-amber-200">
                    <AlertTriangle size={48} className="mx-auto text-amber-500" />
                    <h2 className="mt-4 text-xl font-semibold text-amber-800">Đã xảy ra lỗi</h2>
                    <p className="text-amber-600 mt-2">{error}</p>
                </div>
            );
        }

        if (plan) {
            return (
                <ConversationView
                    planData={plan}
                    planChatHistory={planChatHistory}
                    qaChatHistory={qaChatHistory}
                    onUpdatePlan={handleUpdatePlan}
                    onAskQuestion={handleAskQuestion}
                    onExecute={handleExecutePlan}
                    onReset={() => window.location.reload()} 
                    isSending={isSendingMessage}
                    isExecuting={isExecuting}
                />
            );
        }

        return <Spinner />;
    };

    return (
        <div className="animate-fade-in">
            <h1 className="text-3xl font-bold text-slate-800 mb-6">Thông Báo & Cảnh Báo</h1>
            {renderContent()}
        </div>
    );
};

export default NotificationPage;