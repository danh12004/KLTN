import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Leaf, LogIn } from 'lucide-react';

const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(username, password);
        } catch (err) {
            setError('Tên đăng nhập hoặc mật khẩu không đúng.');
        } finally {
            setLoading(false); 
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-100">
            <div className="w-full max-w-sm p-8 space-y-6 bg-white rounded-xl shadow-lg">
                <div className="text-center">
                    <Leaf size={40} className="mx-auto text-emerald-500" />
                    <h2 className="mt-4 text-2xl font-bold text-slate-800">Trợ Lý Nông Nghiệp AI</h2>
                    <p className="mt-1 text-sm text-slate-500">Vui lòng đăng nhập để tiếp tục</p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <input
                        type="text"
                        placeholder="Tên đăng nhập (vd: nongdan1, admin)"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        required
                    />
                    <input
                        type="password"
                        placeholder="Mật khẩu (vd: password1, 123456)"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        required
                    />
                    {error && <p className="text-sm text-red-600 text-center">{error}</p>}
                    <button type="submit" disabled={loading} className="w-full flex justify-center items-center gap-2 py-2 px-4 font-semibold text-white bg-emerald-600 rounded-md hover:bg-emerald-700 disabled:bg-slate-400">
                        {loading ? 'Đang đăng nhập...' : <><LogIn size={18} /> Đăng nhập</>}
                    </button>
                </form>
            </div>
        </div>
    );
};
export default LoginPage;