import axios from './axiosConfig.js';

// ========================================================================
// APIS PARA SNAPSHOTS DIARIOS
// ========================================================================

export const finalizarDiaSnapshot = async (programId, fecha, importarAvances = false, notas = '') => {
    try {
        const data = {
            fecha: fecha,
            importar_avances: importarAvances,
            notas: notas
        };
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/finalizar-dia-snapshot/`, data);
        return response.data;
    } catch (error) {
        console.error('Error finalizando día con snapshot:', error);
        throw error;
    }
};

export const obtenerHistorialSnapshots = async (programId, dias = 30) => {
    try {
        const response = await axios.get(`/gestion/api/v1/programas/${programId}/snapshots/historial/?dias=${dias}`);
        return response.data;
    } catch (error) {
        console.error('Error obteniendo historial de snapshots:', error);
        throw error;
    }
};

export const compararSnapshots = async (programId, fechaDesde, fechaHasta) => {
    try {
        const response = await axios.get(
            `/gestion/api/v1/programas/${programId}/snapshots/comparacion/?desde=${fechaDesde}&hasta=${fechaHasta}`
        );
        return response.data;
    } catch (error) {
        console.error('Error comparando snapshots:', error);
        throw error;
    }
};

export const obtenerDetalleSnapshot = async (snapshotId) => {
    try {
        const response = await axios.get(`/gestion/api/v1/snapshots/${snapshotId}/detalle/`);
        return response.data;
    } catch (error) {
        console.error('Error obteniendo detalle de snapshot:', error);
        throw error;
    }
};

// ========================================================================
// APIS MEJORADAS PARA PLANIFICACIÓN
// ========================================================================

export const verificarPlanificacionLista = async (programId) => {
    try {
        const response = await axios.get(`/gestion/api/v1/programas/${programId}/verificar-planificacion/`);
        return response.data;
    } catch (error) {
        console.error('Error verificando planificación:', error);
        throw error;
    }
};

export const generarJsonBase = async (programId, fecha = null) => {
    try {
        const data = {};
        if (fecha) data.fecha = fecha;
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/generar-json-base/`, data);
        return response.data;
    } catch (error) {
        console.error('Error generando JSON base:', error);
        throw error;
    }
};

export const cargarJsonBase = async (programId, fecha = null) => {
    try {
        const params = fecha ? `?fecha=${fecha}` : '';
        const response = await axios.get(`/gestion/api/v1/programas/${programId}/json-base/${params}`);
        return response.data;
    } catch (error) {
        console.error('Error cargando JSON base:', error);
        throw error;
    }
};

export const guardarCambiosPlanificacion = async (programId, cambios, fecha = null) => {
    try {
        const data = {
            cambios: cambios,
            fecha: fecha || new Date().toISOString().split('T')[0]
        };
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/guardar-cambios/`, data);
        return response.data;
    } catch (error) {
        console.error('Error guardando cambios:', error);
        throw error;
    }
};

// ========================================================================
// API PRINCIPAL (MANTENER COMPATIBILIDAD)
// ========================================================================

// Mantener función original pero apuntando a nueva implementación
export const finalizarDia = async (programId, fecha, importarAvances = false) => {
    // Redirigir a la nueva implementación con snapshot
    return finalizarDiaSnapshot(programId, fecha, importarAvances);
};

// Exportar todas las funciones
export const planificacionAPI = {
    // Snapshots
    finalizarDiaSnapshot,
    obtenerHistorialSnapshots,
    compararSnapshots,
    obtenerDetalleSnapshot,
    
    // Planificación
    verificarPlanificacionLista,
    generarJsonBase,
    cargarJsonBase,
    guardarCambiosPlanificacion,
    
    // Compatibilidad
    finalizarDia
};

export default planificacionAPI;


/**
 * 
 * 
export const verificarPlanificacionLista = async (programId) => {
    try {
        const response = await axios.get(`/gestion/api/v1/programas/${programId}/verificar-planificacion/`);
        return response.data;
    } catch (error) {
        console.error('Error verificando planificación:', error);
        throw error;
    }
};

// Generar JSON base del día
export const generarJsonBase = async (programId, fecha = null) => {
    try {
        const data = {};
        if (fecha) data.fecha = fecha;
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/generar-json-base/`, data);
        return response.data;
    } catch (error) {
        console.error('Error generando JSON base:', error);
        throw error;
    }
};

// Guardar cambios de planificación
export const guardarCambiosPlanificacion = async (programId, cambios, fecha = null) => {
    try {
        const data = {
            cambios: cambios,
            fecha: fecha || new Date().toISOString().split('T')[0]
        };
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/guardar-cambios/`, data);
        return response.data;
    } catch (error) {
        console.error('Error guardando cambios:', error);
        throw error;
    }
};

// Finalizar día
export const finalizarDia = async (programId, fecha, importarAvances = false) => {
    try {
        const data = {
            fecha: fecha,
            importar_avances: importarAvances
        };
        
        const response = await axios.post(`/gestion/api/v1/programas/${programId}/finalizar-dia/`, data);
        return response.data;
    } catch (error) {
        console.error('Error finalizando día:', error);
        throw error;
    }
};

export const cargarJsonBase = async (programId, fecha = null) => {
    try {
        const params = fecha ? `?fecha=${fecha}` : '';
        const response = await axios.get(`/gestion/api/v1/programas/${programId}/json-base/${params}`);
        return response.data;
    } catch (error) {
        console.error('Error cargando JSON base:', error);
        throw error;
    }
};

// Exportar para uso fácil
export const planificacionAPI = {
    verificarPlanificacionLista,
    generarJsonBase,
    guardarCambiosPlanificacion,
    finalizarDia
};
 * 
 */