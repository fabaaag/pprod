import axios from './axiosConfig';

// Listar todos los operadores activos
export const getOperadores = () => axios.get('/gestion/api/produccion/operadores/');

// Dashboard del operador con asignaciones y estadísticas
export const getDashboardOperador = (operadorId) => 
  axios.get(`/gestion/api/produccion/operador/${operadorId}/dashboard/`);

// Obtener formulario de ingreso (asignaciones disponibles)
export const getFormularioIngreso = (operadorId) => 
  axios.get(`/gestion/api/produccion/operador/${operadorId}/ingresar/`);

// Procesar ingreso de producción
export const procesarIngreso = (operadorId, data) => 
  axios.post(`/gestion/api/produccion/operador/${operadorId}/ingresar/`, data);

// Obtener historial de producción del operador
export const getHistorialProduccion = (operadorId, params = {}) => 
  axios.get(`/gestion/api/produccion/operador/${operadorId}/historial/`, { params });

// Obtener estadísticas del operador
export const getEstadisticasOperador = (operadorId) => 
  axios.get(`/gestion/api/produccion/operador/${operadorId}/estadisticas/`);

// Obtener detalles de una ruta de OT
export const getDetalleRutaOT = (asignacionId) => 
  axios.get(`/gestion/api/produccion/asignacion/${asignacionId}/detalle/`);

// Obtener fallas disponibles para reportar
export const getFallasDisponibles = () => 
  axios.get('/gestion/api/produccion/fallas/');

// Validar ingreso antes de procesar
export const validarIngreso = (data) => 
  axios.post('/gestion/api/produccion/validar-ingreso/', data);