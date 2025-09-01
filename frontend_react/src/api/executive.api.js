import axios from "./axiosConfig";

// ============= DASHBOARD EJECUTIVO APIS =============

// API DE PRUEBA (temporal)
export const testApiConnectivity = async () => {
  try {
    const response = await axios.get('/gestion/api/test/connectivity/');
    return response.data;
  } catch (error) {
    console.error('Error en conectividad:', error);
    throw error;
  }
};

export const testDashboardBase = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/test/dashboard/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error en dashboard de prueba:', error);
    throw error;
  }
};

export const getDashboardEjecutivo = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/dashboard/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar dashboard ejecutivo:', error);
    throw error;
  }
};

export const getProduccionFisica = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/produccion/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar métricas de producción:', error);
    throw error;
  }
};

export const getEficienciaOperacional = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/eficiencia/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar métricas de eficiencia:', error);
    throw error;
  }
};

export const getCumplimientoEntregas = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/entregas/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar métricas de entregas:', error);
    throw error;
  }
};

export const getCostosEstimados = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/costos/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar métricas de costos:', error);
    throw error;
  }
};

export const getComparativasHistoricas = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/comparativas/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar comparativas históricas:', error);
    throw error;
  }
};

export const getAlertasEjecutivas = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/alertas/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar alertas ejecutivas:', error);
    throw error;
  }
};

export const getProyeccionesPrograma = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/proyecciones/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar proyecciones:', error);
    throw error;
  }
};

export const getMetricasTiempoReal = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/tiempo-real/${programaId}/`);
    return response.data;
  } catch (error) {
    console.error('Error al cargar métricas en tiempo real:', error);
    throw error;
  }
};

export const getKpisConsolidados = async () => {
  try {
    const response = await axios.get('/gestion/api/jobmanagement/executive/consolidado/');
    return response.data;
  } catch (error) {
    console.error('Error al cargar KPIs consolidados:', error);
    throw error;
  }
};

export const configurarParametrosCostos = async (parametros) => {
  try {
    const response = await axios.post('/gestion/api/jobmanagement/executive/configurar-costos/', parametros);
    return response.data;
  } catch (error) {
    console.error('Error al configurar parámetros de costos:', error);
    throw error;
  }
};

export const generarReporteEjecutivoPDF = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/jobmanagement/executive/pdf/${programaId}/`, {
      responseType: 'blob',
      timeout: 30000
    });

    // Crear blob para descargar PDF
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte_ejecutivo_programa_${programaId}.pdf`;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);

    return true;
  } catch (error) {
    console.error('Error al generar reporte ejecutivo PDF:', error);
    throw error;
  }
}; 