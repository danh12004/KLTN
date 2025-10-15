import React, { useState, useEffect, useRef } from 'react';
import api from '../../api';
import { Send, Bot, User } from 'lucide-react';

const ChatBubble = ({ message }) => {
    const isUser = message.sender === 'user';
    const isLoading = message.text === '...';
    return (
        <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''}`}>
            {!isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><Bot size={20} className="text-slate-600" /></div>}
            <div className={`px-4 py-3 rounded-2xl max-w-lg shadow-sm ${isUser ? 'bg-emerald-600 text-white rounded-br-none' : 'bg-slate-100 text-slate-800 rounded-bl-none'}`}>
                {isLoading ? (
                    <div className="flex items-center gap-2">
                        <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce"></span>
                    </div>
                ) : (
                    <p className="text-sm" dangerouslySetInnerHTML={{ __html: message.text.replace(/\n/g, '<br />') }} />
                )}
            </div>
            {isUser && <div className="flex-shrink-0 w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center"><User size={20} className="text-slate-600" /></div>}
        </div>
    );
};

const QAPage = () => {
    const [history, setHistory] = useState([
        { sender: 'ai', text: 'Chào bác, tôi là Trợ lý Nông nghiệp AI. Bác có câu hỏi gì về kỹ thuật canh tác hoặc tình hình nông trại của mình không ạ?' }
    ]);
    const [message, setMessage] = useState('');
    const [isSending, setIsSending] = useState(false);
    const chatEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history]);

    useEffect(() => {
        if (!isSending && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isSending]); 

    const handleSendMessage = async () => {
        if (!message.trim()) return;

        const userMessage = { sender: 'user', text: message };
        setHistory(prev => [...prev, userMessage]);
        setMessage('');
        setIsSending(true);

        try {
            const response = await api.post('/farm/ask', {
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
                            ref={inputRef}
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
                            className="flex-shrink-0 bg-emerald-600 text-white p-3 rounded-lg hover:bg-emerald-700 transition disabled:bg-slate-400 disabled:cursor-not-allowed"
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