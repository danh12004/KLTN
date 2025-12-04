import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SettingsProvider } from './context/SettingsContext';
import LoginPage from './pages/LoginPage';
import FarmerLayout from './layouts/FarmerLayout';
import AdminLayout from './layouts/AdminLayout'; 
import Spinner from './components/Spinner';
import { Toaster } from 'react-hot-toast';

const ProtectedRoute = ({ children, role }) => {
    const { user, loading } = useAuth();

    if (loading) {
        return <div className="flex h-screen items-center justify-center"><Spinner /></div>;
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    if (role && user.role !== role) {
        return <Navigate to={user.role === 'admin' ? '/admin' : '/farmer'} replace />;
    }

    return children;
};

const AppRoutes = () => {
    const { user } = useAuth();
    return (
        <Routes>
            <Route 
                path="/login" 
                element={
                    !user ? <LoginPage /> 
                    : <Navigate to={user.role === 'admin' ? '/admin' : '/farmer'} replace />
                } 
            />
            
            <Route path="/farmer/*" element={
                <ProtectedRoute role="farmer"><FarmerLayout /></ProtectedRoute>
            } />

            <Route path="/admin/*" element={
                <ProtectedRoute role="admin"><AdminLayout /></ProtectedRoute>
            } />
            
            <Route path="*" element={<Navigate to={user ? (user.role === 'admin' ? '/admin' : '/farmer') : '/login'} />} />
        </Routes>
    );
}

function App() {
    return (
        <Router>
            <AuthProvider>
                <SettingsProvider>
                    <AppRoutes />
                    <Toaster position="top-right" reverseOrder={false} />
                </SettingsProvider>
            </AuthProvider>
        </Router>
    );
}

export default App;
