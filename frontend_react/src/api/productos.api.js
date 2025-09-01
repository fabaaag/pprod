import axios from 'axios';
import axiosInstance from './axiosConfig';

// API para Productos
export const getProductos = async (params = {}) => {
    try {
        const response = await axiosInstance.get('/productos/productos/', { params });
        return response.data;
    } catch (error) {
        console.error('Error al obtener productos:', error);
        throw error;
    }
};

export const getProducto = async (id) => {
    try {
        const response = await axiosInstance.get(`/productos/productos/${id}/`);
        return response.data;
    } catch (error) {
        console.error(`Error al obtener producto con ID ${id}:`, error);
        throw error;
    }
};

// API para Piezas
export const getPiezas = async (params = {}) => {
    try {
        const response = await axiosInstance.get('/productos/piezas/', { params });
        return response.data;
    } catch (error) {
        console.error('Error al obtener piezas:', error);
        throw error;
    }
};

export const getPieza = async (id) => {
    try {
        const response = await axiosInstance.get(`/productos/piezas/${id}/`);
        return response.data;
    } catch (error) {
        console.error(`Error al obtener pieza con ID ${id}:`, error);
        throw error;
    }
};

// API para Familias y Subfamilias
export const getFamilias = async (params = {}) => {
    try {
        const response = await axiosInstance.get('/productos/familias/', { params });
        return response.data;
    } catch (error) {
        console.error('Error al obtener familias:', error);
        throw error;
    }
};

export const getSubfamilias = async (params = {}) => {
    try {
        const response = await axiosInstance.get('/productos/subfamilias/', { params });
        return response.data;
    } catch (error) {
        console.error('Error al obtener subfamilias:', error);
        throw error;
    }
};

// Obtener máquinas compatibles para un proceso
export const getMaquinasCompatibles = async (procesoId, tipo, objetoId) => {
    try {
        const response = await axiosInstance.get(`/gestion/api/v1/maquinas-compatibles/1/`, {
            params: {
                proceso_id: procesoId,
                tipo: tipo,
                objeto_id: objetoId
            }
        });
        return response.data.maquinas_compatibles;
    } catch (error) {
        console.error('Error obteniendo máquinas compatibles:', error);
        throw error;
    }
};



export const getRutasProceso = async(objetoId) => {
    try {
        const response = await axiosInstance.get(`/productos/rutas-proceso/${objetoId}/`, {
            params: { tipo }
       });
       return response.data;
    } catch (error){
        console.error('Error obteniendo rutas por proceso:', error);
        throw error;
    }
};

// Actualizar estándar de producción
export const actualizarEstandar = async (rutaId, maquinaId, estandar, esPrincipal) => {
    try {
        const response = await axiosInstance.post(`/productos/actualizar-estandar-ruta/${rutaId}/`, {
            maquina_id: maquinaId,
            estandar: estandar,
            es_principal: esPrincipal
        });
        return response.data;
    } catch (error) {
        console.error('Error actualizando estándar:', error);
        throw error;
    }
};

export const getEstandaresProceso = async (procesoId, tipo, objetoId) => {
    try {
        //Verificar que objetoId exista y sea un número
        if (!objetoId) {
            console.error('Error: objetoId no existe');
            return [];
        }
        //Asegurarse de que objetoId sea número
        const objetoIdNumb = parseInt(objetoId);

        const params = {};
        if (tipo === 'producto'){
            params.producto_id = objetoIdNumb;
        } else if (tipo === 'pieza') {
            params.pieza_id = objetoIdNumb;
        } else {
            console.error('Error: tipo debe ser "producto" o "pieza"');
            return [];
        }

        console.log("######params:", params);

        const response = await axiosInstance.get(`/productos/estandares-proceso/${procesoId}/`, { params });
        return response.data;
    } catch (error) {
        console.error('Error obteniendo estándares por proceso:', error);
        // Devolver array vacío para evitar errores en el componente
        return [];
    }
};

/**
 * Busca los estándares guardados para un producto o pieza
 */
export const obtenerEstandaresProducto = async (productoId) => {
    try{
        const response = await axiosInstance.get(`/productos/${productoId}/estandares/`);
        return response.data;
    } catch (error){
        console.error('Error obteniendo estándares del producto:', error);
        throw error;
    }
};

export const obtenerEstandaresMultiples = async (productosIds) => {
    try {
        const response = await axiosInstance.post(`/productos/estandares-multiples/`, {
            productos_ids: productosIds
        });
        return response.data;
    } catch (error) {
        console.error('Error obteniendo estándares de productos:', error);
        throw error;
    }
}