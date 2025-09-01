import axios from "./axiosConfig";



export const createProgram = (program) => axios.post(`/gestion/api/v1/programas/crear_programa/`, program);

export const getAllPrograms = () => axios.get(`/gestion/api/v1/programas/`);

export const deleteProgram = async (id) => {
  try {
      const response = await axios.delete(`/gestion/api/v1/programas/${id}/delete/`);
      return response.data
  } catch (error) {
      console.log("Error eliminando programas:", error)
      throw error
  }
};

export const updateProgram = async (programId, updates) => {
  try{
    const response = await axios.put(`/gestion/api/v1/programas/${programId}/update-prio/`,
      {
        order_ids: updates.map(orden => ({
          id: orden.orden_trabajo,
          priority: orden.priority,
          procesos: orden.procesos.map(proceso => ({
            id: proceso.id,
            maquina_id: proceso.maquina_id,
            estandar: proceso.estandar
          }))
        })),
        recalculate_dates: true
      },
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error actualizando programa:", error);
    throw error;
  }
};

export const getProgram = async (programId) => {
  try {
    if (!programId) {
      console.error('programId is undefined');
      throw new Error('programId is required');
    }

    let programResponse, asignacionesResponse;
    
    try {
      programResponse = await axios.get(`/gestion/api/v1/programas/${programId}/`);
    } catch (error) {
      console.error('Error obteniendo datos del programa:', error);
      throw error;
    }

    const program = programResponse.data;
    
    return program;
  } catch (error) {
    console.error('Error fetching program:', error);
    throw error;
  }
};
  
export const updatePriorities = async (programId, orderIds) => {
  try {
    const response = await axios.put(
      `/gestion/api/v1/programas/${programId}/update-prio/`,
      { 
        order_ids: orderIds,
        recalculate_dates: true
      },
      {
        headers: {
          'Content-Type':'application/json',
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error actualizando prioridades", error);
    throw error;
  }
};
  
export const deleteOrder = async (programId, orderId) => {
  try{
    console.log(orderId);
    const response = await axios.delete(`/machine/api/v1/programas/${programId}/delete-orders/`, {
      data: { order_ids:[orderId] },
      headers: {
        'Content-Type': 'application/json',
      },
      validateStatus: function (status) {
        return status >= 200 && status < 300;
      }
    });
    return response.data.result;
  }catch(error){
    if (error.response){
      throw error.response.data;
    }
    throw error;
  }
};

export const getMaquinas = async (programId, procesoCodigo = null) => {
  if(!programId){
    throw new Error("Se requiere un ID de programa");
  }  
  const url = procesoCodigo
      ? `/gestion/api/v1/programas/${programId}/maquinas/?proceso_codigo=${procesoCodigo}`
      : `/gestion/api/v1/programas/${programId}/maquinas/`;
      //console.log(`[API] Solicitando máquinas con URL: ${url}`);
      //console.log(`[API] Parámetros: programId=${programId}, procesoCodigo=${procesoCodigo}`);

  try{
    const response = await axios.get(url);
    return response.data;
  }catch(error){
    console.error(`[API] Error fetching maquinas:`, error);
    console.error(`[API] URL que falló: ${url}`);
    
    if (error.response) {
      console.error(`[API] Datos de respuesta de error:`, error.response.data);
      console.error(`[API] Estado de respuesta de error:`, error.response.status);
    }
    
    throw error;
  }
};

export const generateProgramPDF = async (programId) => {
  try{
    const response = await axios.get(`/gestion/api/v1/programas/${programId}/generar_pdf/`, {
      responseType: 'blob',
      timeout: 30000 //Aumentar el timeout a 30 segundos
    });

    console.log("Respuesta recibida, creando blob...");

    //Verificar que la respuesta sea un PDF válido
    if(response.headers['content-type'] !== 'application/pdf'){
      console.error("La respuesta no es un PDF:", response.headers['content-type']);

      //Si no es un PDF, intentar leer el contenido como texto
      const text =  await response.data.text();
      try {
        const errorData = JSON.parse(text);
        throw new Error(errorData.detail || errorData.message || "La respuesta no es un PDF válido");
      } catch (e) {
        throw new Error("La respuesta no es un PDF válido");
      }
    }

    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);

    console.log("Blob creado, descargando PDF...");

    const a = document.createElement('a');
    a.href = url;
    a.download = `programa_${programId}.pdf`;
    document.body.appendChild(a);
    a.click();


    setTimeout(() => {
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    }, 100);

    console.log("PDF descargado exitosamente");
    return true;
  } catch(error){
    console.error('Error generando PDF:', error);
    throw error;
  }
};

export const getProcesoTimeline = async (programaId, procesoId) => {
  try{
    const response = await axios.get(`/gestion/api/v1/programas/${programaId}/procesos/${procesoId}/timeline/`);
    return response.data;
  } catch (error){
    console.error(`[API] Error obteniendo timeline para proceso:`, error);
    throw error;
  }
}

export const getSupervisorReport = async (programId) => {
  try {
      const response = await axios.get(`/gestion/api/v1/programas/${programId}/supervisor-report/`);
      return response.data;
  } catch (error) {
      console.error('Error en getSupervisorReport:', error);
      throw error;
  }
};

export const updateSupervisorReport = async (programId, data) => {
    // Si recibimos un objeto con 'tasks', procesamos cada tarea individualmente
    if (data.tasks && Array.isArray(data.tasks)) {
        try {
            const results = [];
            for (const task of data.tasks) {
                const response = await axios.put(
                    `/gestion/api/v1/programas/${programId}/supervisor-report/update-priority/`,
                    {
                        tarea_id: task.id,
                        proceso_id: task.proceso_id,
                        kilos_fabricados: task.kilos_fabricados,
                        cantidad_programada: task.cantidad_programada,
                        fecha: task.fecha,
                        estado: task.estado,
                        observaciones: task.observaciones
                    },
                    {
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }
                );
                results.push(response.data);
            }
            return results;
        } catch (error) {
            console.error('Error en updateSupervisorReport:', error);
            throw error;
        }
    } else {
        // Si recibimos una sola tarea, la procesamos directamente
        try {
            const response = await axios.post(
                `/gestion/api/v1/programas/${programId}/supervisor-report/update-priority/`,
                data,
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            return response.data;
        } catch (error) {
            console.error('Error en updateSupervisorReport:', error);
            throw error;
        }
    }
};

/**
 * Finaliza el día creando continuaciones para tareas incompletas
 * @param {number} programId - ID del programa
 * @param {string} fecha - Fecha en formato YYYY-MM-DD
 * @returns {Promise} - Promesa con los resultados de la finalización
 */
export const finalizarDia = async (programId, fecha = null) => {
  try {
    const numericProgramId = parseInt(programId, 10);
    const data = fecha ? { fecha } : {};
    const response = await axios.post(`/gestion/api/v1/programas/${numericProgramId}/finalizar-dia/`, data);
    return response.data;
  } catch (error) {
    console.error('Error finalizando día:', error);
    throw error;
  }
};

/**
 * Obtiene la información de genealogía de una tarea específica
 * @param {number} taskId - ID de la tarea
 * @returns {Promise} - Promesa con los datos de genealogía de la tarea
 */
export const obtenerGenealogiaTask = async (taskId) => {
  try {
    // Convertir taskId a número si es un string formateado por ReactSortable
    const numericTaskId = typeof taskId === 'string' && taskId.startsWith('item_')
        ? parseInt(taskId.split('_')[1])
        : parseInt(taskId, 10);
        
    const response = await axios.get(`/gestion/api/v1/tareas/${numericTaskId}/genealogia/`);
    return response.data;
  } catch (error) {
    console.error('Error obteniendo genealogía de tarea:', error);
    throw error;
  }
};


// Obtener timeline de ejecución
export const getProgramTimelineEjecucion = async (programId) => {
  try {
    const response = await axios.get(`/gestion/api/v1/programas/${programId}/timeline-ejecucion/`);
    return response.data;
  } catch (error) {
    console.error("Error obteniendo timeline de ejecución:", error);
    throw error;
  }
};

export const checkProgramStatus = async (programId) => {
  try {
    const response = await axios.post(
      `/gestion/api/v1/programas/${programId}/check-status/`,
      {},
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error verificando estado del programa:', error);
    throw error;
  }
};

export const addOrdersToProgram = async (programId, orderIds) => {
  try {
    const response = await axios.post(
      `/gestion/api/v1/programas/${programId}/add-orders/`,
      { ordenes: orderIds },
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error añadiendo órdenes al programa:", error);
    throw error;
  }
};

export const getUnassignedOrders = async () => {
  try {
    const response = await axios.get(`/gestion/api/v1/ordenes/no_asignadas/`);
    return response.data;
  } catch (error) {
    console.error("Error obteniendo órdenes sin asignar:", error);
    throw error;
  }
};

export const verificarReajustesPrograma = async (programId) => {
  try {
    const response = await axios.post(
      `/gestion/api/v1/programas/${programId}/reajustar/`
    );
    return response.data;
  } catch (error) {
    console.error("Error verificando reajustes:", error);
    throw error;
  }
};

export const aplicarReajustesPrograma = async (programId, ajustes) => {
  try {
      const response = await axios.put(
          `/gestion/api/v1/programas/${programId}/reajustar/`,
          {
              ajustes_sugeridos: ajustes
          },
          {
              headers: {
                  'Content-Type': 'application/json'
              }
          }
      );
      return response.data;
  } catch (error) {
      console.error("Error aplicando reajustes:", error);
      throw error;
  }
};


// En programs.api.js
export const getProgramHistory = async (programId, fecha = null) => {
  try {
        const url = fecha 
            ? `/gestion/api/v1/programas/${programId}/historial/?fecha=${fecha}`
            : `/gestion/api/v1/programas/${programId}/historial/`;
        const response = await axios.get(url);
      return response.data;
  } catch (error) {
      console.error('Error obteniendo historial del programa:', error);
      throw error;
  }
};

export const deleteProgramHistory = async (programId, historialId) => {
    try {
        const response = await axios.delete(
            `/gestion/api/v1/programas/${programId}/historial/${historialId}/`
        );
        return response.data;
    } catch (error) {
        console.error('Error eliminando historial:', error);
        throw error;
    }
};
// Obtener timeline de planificación (nuevo)
export const getProgramTimelinePlanning = async (programId, fecha = null) => {
  try {
    let url = `/gestion/api/v1/programas/${programId}/timeline-planificacion/`;
    if (fecha) {
      url += `?fecha=${fecha}`;
    }
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    console.error("Error obteniendo timeline de planificación:", error);
    throw error;
  }
};

export const updateProductStandard = async (programId, itemRutaId) => {
  try{
    const response = await axios.post(
      `/gestion/api/v1/programas/${programId}/update-product-standard/`,
      { item_ruta_id: itemRutaId },
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error actualizando estándar del producto:', error);
    throw error;
  }
};


// ========================================================================
// FUNCIONES PARA PROGRESO DIRECTO DE ITEMRUTA - AÑADIR AL FINAL
// ========================================================================

// Actualizar progreso de ItemRuta directamente
export const updateItemRutaProgress = async (itemRutaId, progressData) => {
  try {
    const response = await axios.patch(
      `/gestion/api/v1/item-ruta/${itemRutaId}/progreso/`,
      progressData,
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error actualizando progreso ItemRuta:", error);
    throw error;
  }
};

// Previsualizar reagendamiento
export const previewReagendarPrograma = async (programId) => {
  try {
    const response = await axios.get(
      `/gestion/api/v1/programas/${programId}/reagendar-inteligente/`
    );
    return response.data;
  } catch (error) {
    console.error("Error previewing reagendamiento:", error);
    throw error;
  }
};

// Aplicar reagendamiento
export const aplicarReagendarPrograma = async (programId, options = {}) => {
  try {
    const response = await axios.post(
      `/gestion/api/v1/programas/${programId}/reagendar-inteligente/`,
      options,
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error("Error aplicando reagendamiento:", error);
    throw error;
  }
};

// Timeline tiempo real con progreso (nueva)
export const getTimelineTimeRealWithProgress = async (programaId) => {
  try {
    const response = await axios.get(`/gestion/api/v1/programas/${programaId}/timeline-tiempo-real/`);
    return response.data;
  } catch (error) {
    console.error('Error obteniendo timeline tiempo real:', error);
    throw error;
  }
};


export const updateItemRutaEstado = async (itemRutaId, nuevoEstado) => {
  try {
      const response = await axios.patch(`/gestion/api/v1/item-ruta/${itemRutaId}/estado/`, {
          estado_proceso: nuevoEstado
      });
      return response.data;
  } catch (error) {
      console.error('Error actualizando estado ItemRuta:', error);
      throw error;
  }
};

export const cargarEstandarInicial = async (otId, procesoId, maquinaId, programId) => {
  try {
    const response = await axios.get(`api/v1/programas/${programId}/update-estandar-from-start/`, {
      params: {
        ot_id: otId,
        proceso_id: procesoId,
        maquina_id: maquinaId
      }
    });
    console.log(response.data);
    return response.data.estandar;
  } catch (error) {
      console.error('Error obteniendo estandares iniciales', error);
      throw error;
  }
};

export const updateItemRutaStates = (programId) => {
    return axios.post(`/gestion/api/v1/programas/${programId}/update-item-states/`);
};


// ========================================================================
// FUNCIONES PARA FECHAS PLANIFICADAS DE PROCESOS
// ========================================================================

/**
 * Obtiene las fechas planificadas para un proceso específico
 * @param {number} programId - ID del programa de producción
 * @param {number} itemRutaId - ID del ItemRuta (proceso)
 * @returns {Promise} - Promesa con las fechas planificadas
 */
export const getProcesoFechasPlanificadas = async (programId, itemRutaId) => {
  try {
    console.log(`[API] Solicitando fechas para programa ${programId}, proceso ${itemRutaId}`);
    
    const response = await axios.get(
      `/gestion/api/v1/programas/${programId}/procesos/${itemRutaId}/fechas-planificadas/`
    );
    
    console.log(`[API] Fechas obtenidas:`, response.data);
    return response.data;
    
  } catch (error) {
    console.error('Error obteniendo fechas planificadas:', error);
    
    // Si es un 404, retornar null en lugar de lanzar error
    if (error.response?.status === 404) {
      console.log('[API] No hay fechas planificadas (404 - normal)');
      return null;
    }
    
    // Para otros errores, lanzar la excepción
    throw error;
  }
};

/**
 * Obtiene todos los items de timeline para un proceso específico con detalles completos
 * @param {number} programId - ID del programa de producción  
 * @param {number} itemRutaId - ID del ItemRuta (proceso)
 * @returns {Promise} - Promesa con los items de timeline del proceso
 */
export const getProcesoTimelineItems = async (programId, itemRutaId) => {
  try {
    const response = await axios.get(
      `/gestion/api/v1/programas/${programId}/procesos/${itemRutaId}/timeline-items/`
    );
    return response.data;
  } catch (error) {
    console.error('Error obteniendo timeline items del proceso:', error);
    
    // Si es un 404, no hay items de timeline
    if (error.response?.status === 404) {
      return { items: [], resumen: null };
    }
    
    throw error;
  }
};