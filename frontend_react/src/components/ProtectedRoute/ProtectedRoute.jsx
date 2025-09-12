import { Navigate } from "react-router-dom";
import { checkAuthStatus } from "../../api/auth.api";

export function ProtectedRoute({ children, allowedRoles = [] }) {
    const { isAuthenticated, user } = checkAuthStatus();

    // 🔍 LOGS TEMPORALES PARA DEBUGGEAR
    console.log('=== DEBUG PROTECTED ROUTE ===');
    console.log('isAuthenticated:', isAuthenticated);
    console.log('user object:', user);
    console.log('user.rol:', user?.rol);
    console.log('user.role:', user?.role);
    console.log('user.user_type:', user?.user_type);
    console.log('allowedRoles:', allowedRoles);
    console.log('==============================');

    if (!isAuthenticated) {
        return <Navigate to="/login" />;
    }

    //Si se especifican roles permitidos, verificar si el usuario tiene acceso
    if (allowedRoles.length > 0 && !allowedRoles.includes(user?.rol)){
        return <Navigate to="/home" />;
    }

    return children;
}