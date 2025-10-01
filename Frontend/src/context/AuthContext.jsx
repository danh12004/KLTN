import React, { createContext, useState, useContext, useEffect } from 'react';
import api from '../api';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                const decodedUser = jwtDecode(token);
                const currentTime = Date.now() / 1000;
                
                if (decodedUser.exp > currentTime) {
                    setUser({ 
                        id: decodedUser.sub, 
                        role: decodedUser.role, 
                        fullName: decodedUser.fullName 
                    });
                } else {
                    localStorage.removeItem('token');
                }
            } catch (error) {
                console.error('Invalid token:', error);
                localStorage.removeItem('token');
            }
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        try {
            const response = await api.post('/auth/login', { username, password });
            const { access_token } = response.data;

            if (!access_token) {
                throw new Error("Token không được trả về từ server");
            }

            localStorage.setItem('token', access_token);
            const decodedUser = jwtDecode(access_token);
            
            setUser({ 
                id: decodedUser.sub, 
                role: decodedUser.role,
                fullName: decodedUser.fullName
            });
            
            return decodedUser;
        } catch (error) {
            console.error("Login failed:", error);
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);