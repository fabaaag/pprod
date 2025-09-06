import axios from './axiosConfig.js';

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