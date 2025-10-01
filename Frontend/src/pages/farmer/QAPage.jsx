import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../api';
import { Send, Bot, User, MessageCircle } from 'lucide-react';

const ChatBubble = ({ message }) => {
    const isUser = message.sender === 'user';
    return (
        <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''}`}>
            {!isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><Bot size={20} className="text-slate-600" /></div>}
            <div className={`px-4 py-3 rounded-2xl max-w-lg ${isUser ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-800 rounded-bl-none'}`}>
                <p className="text-sm" dangerouslySetInnerHTML={{ __html: message.text.replace(/\n/g, '<br />') }} />
            </div>
            {isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><User size={20} className="text-slate-600" /></div>}
        </div>
    );
};

const QAPage = () => {
    const { user } = useAuth();
    const [history, setHistory] = useState([
        { sender: 'ai', text: 'Chào bác, tôi là Trợ lý Nông nghiệp AI. Bác có câu hỏi gì về tình hình ruộng lúa của mình không ạ?' }
    ]);
    const [message, setMessage] = useState('');
    const [isSending, setIsSending] = useState(false);
    const chatEndRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history]);

    const handleSendMessage = async () => {
        if (!message.trim() || !user?.id) return;

        const userMessage = { sender: 'user', text: message };
        setHistory(prev => [...prev, userMessage]);
        setMessage('');
        setIsSending(true);

        try {
            const response = await api.post('/ask', {
                farmer_id: user.id,
                question: message
            });
            const aiMessage = { sender: 'ai', text: response.data.answer };
            setHistory(prev => [...prev, aiMessage]);
        } catch (error) {
            const errorMessage = { sender: 'ai', text: 'Xin lỗi, đã có lỗi xảy ra. Tôi không thể trả lời câu hỏi này ngay bây giờ.' };
            setHistory(prev => [...prev, errorMessage]);
        } finally {
            setIsSending(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="animate-fade-in flex flex-col h-full">
            <h1 className="text-3xl font-bold text-slate-800 mb-6 shrink-0">Hỏi Đáp Cùng Trợ Lý AI</h1>
            <div className="bg-white rounded-xl shadow-md border border-slate-200 flex flex-col flex-grow min-h-0">
                <div className="flex-1 p-6 space-y-4 overflow-y-auto">
                    {history.map((msg, index) => (
                        <ChatBubble key={index} message={msg} />
                    ))}
                    {isSending && <ChatBubble message={{ sender: 'ai', text: '...' }} />}
                    <div ref={chatEndRef} />
                </div>
                <div className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-xl shrink-0">
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Nhập câu hỏi của bạn..."
                            className="w-full px-4 py-2 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            disabled={isSending}
                        />
                        <button
                            onClick={handleSendMessage}
                            disabled={isSending || !message.trim()}
                            className="flex-shrink-0 bg-emerald-600 text-white p-3 rounded-lg hover:bg-emerald-700 transition disabled:bg-slate-400"
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default QAPage;