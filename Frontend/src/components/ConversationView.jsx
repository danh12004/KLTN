import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, RotateCcw, FileText, MessageSquare } from 'lucide-react'; 
import ResultDisplay from './ResultDisplay';

const ChatBubble = ({ message }) => {
    const isUser = message.sender === 'user';
    return (
        <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''}`}>
            {!isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><Bot size={20} className="text-slate-600" /></div>}
            <div className={`px-4 py-3 rounded-2xl max-w-sm ${isUser ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-800 rounded-bl-none'}`}>
                <p className="text-sm">{message.text}</p>
            </div>
            {isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><User size={20} className="text-slate-600" /></div>}
        </div>
    );
};

const ConversationView = ({ planData, planChatHistory, onUpdatePlan, onExecute, onReset, isSending, isExecuting }) => {
    const [message, setMessage] = useState('');
    const chatEndRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [planChatHistory]);

    const handleSendClick = () => {
        if (message.trim() && !isSending) {
            onUpdatePlan(message); 
            setMessage('');
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendClick();
        }
    };

    const isActionable = planData?.treatment_plan?.is_actionable;

    return (
        <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
            <div className="lg:max-h-[80vh] lg:overflow-y-auto pr-4">
                <ResultDisplay data={planData} />
            </div>
            <div className="bg-white rounded-2xl shadow-lg border border-slate-200 flex flex-col lg:max-h-[80vh]">
                <div className="p-3 font-semibold flex items-center justify-center gap-2 border-b border-slate-200 text-slate-700">
                    Tương tác với Kế hoạch
                </div>
                
                <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                    {planChatHistory.map((msg, index) => (
                        <ChatBubble key={index} message={msg} />
                    ))}
                    <div ref={chatEndRef} />
                </div>
                
                <div className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl space-y-3">
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Yêu cầu thay đổi kế hoạch..." 
                            className="w-full px-4 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 transition"
                            disabled={isSending || isExecuting}
                        />
                        <button
                            onClick={handleSendClick}
                            disabled={isSending || !message.trim()}
                            className="flex-shrink-0 bg-emerald-600 text-white p-3 rounded-lg hover:bg-emerald-700 transition disabled:bg-slate-400 disabled:cursor-not-allowed"
                        >
                            {isSending ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> : <Send size={20} />}
                        </button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                        <button 
                            onClick={onReset}
                            className="w-full flex items-center justify-center gap-2 bg-slate-500 text-white font-semibold py-2 px-4 rounded-lg hover:bg-slate-600 transition"
                        >
                            <RotateCcw size={18} />
                            Tải lại
                        </button>
                        <button
                            onClick={onExecute}
                            disabled={!isActionable || isExecuting || isSending}
                            className="w-full flex items-center justify-center gap-2 bg-green-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-green-700 transition disabled:bg-slate-400 disabled:cursor-not-allowed"
                        >
                            {isExecuting ? 'Đang gửi lệnh...' : (isActionable ? 'Xác nhận & Thực thi' : 'Không cần hành động')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConversationView;