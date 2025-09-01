export const processCalculations = {
    //Calcular tiempo estimado basado en estándar y cantidad
    calcularTiempoEstimado: (cantidad, estandar) => {
        if (!estandar || estandar <= 0) return 0;
        return cantidad / estandar;
    },

    //Verificar si hay procesos con estándar en cero
    verificarEstandaresCero: (ots) => {
        const procesosConEstandarCero = [];

        ots.forEach(ot => {
            ot.procesos?.forEach(proceso => {
                if (!proceso.estandar || proceso.estandar <= 0){
                    procesosConEstandarCero.push({
                        ot_codigo: ot.orden_trabajo_codigo_ot,
                        proceso_descripcion: proceso.descripcion
                    });
                }
            });
        });

        return procesosConEstandarCero;
    },

    //Calcular métricas de producción
    calcularMetricas: (ots) => {
        const metricas = {
            totalKilosPlanificados: 0,
            totalKilosFabricados: 0,
            totalProcesos: 0,
            procesosCompletados: 0,
            procesosEnProceso: 0,
            procesosPendientes: 0,
            eficienciaPromedio: 0,
            valorTotalPrograma: 0,
            valorTotalFabricado: 0,
        };

        ots.forEach(ot => {
            ot.procesos?.forEach(proceso => {
                metricas.totalProcesos++;
                metricas.totalKilosPlanificados += (ot.orden_trabajo_cantidad_pedido * ot.orden_trabajo_peso) || 0;
                //console.log('ot.cantidad_avance:', ot.orden_trabajo_cantidad_avance, 'ot.peso:', ot.orden_trabajo_peso, ot.orden_trabajo_cantidad_pedido, ot.orden_trabajo_valor);
                metricas.totalKilosFabricados += ot.orden_trabajo_cantidad_avance * ot.orden_trabajo_peso || 0;
                metricas.valorTotalPrograma += ot.orden_trabajo_valor * ot.orden_trabajo_cantidad_pedido || 0;
                metricas.valorTotalFabricado += ot.orden_trabajo_valor * ot.orden_trabajo_cantidad_avance || 0;


                switch (proceso.estado_proceso){
                    case 'COMPLETADO':
                        metricas.procesosCompletados++;
                        break;
                    case 'EN_PROCESO':
                        metricas.procesosEnProceso++;
                        break;
                    default:
                        metricas.procesosPendientes++;
                }

                if (proceso.tiempo_real && proceso.tiempo_estimado){
                    metricas.eficienciaPromedio += (proceso.tiempo_estimado / proceso.tiempo_real) * 100;
                }
            });
        });

        if (metricas.totalProcesos > 0){
            metricas.eficienciaPromedio /= metricas.totalProcesos;
        }

        return metricas;
    },

    //Verificar inconsistencias en los procesos
    verificarInconsistencias: (ots) => {
        const inconsistencias = [];

        ots.forEach(ot => {
            let avanceAnterior = 0;
            let procesoAnterior = null;

            ot.procesos?.forEach(proceso => {
                const avanceActual = proceso.porcentaje_completado || 0;

                //Verificar secuencia de avances
                if(avanceActual < avanceAnterior - 1){
                    inconsistencias.push({
                        tipo: 'SECUENCIA_INVALIDA',
                        ot_codigo: ot.orden_trabajo_codigo_ot,
                        proceso_actual: proceso.descripcion,
                        proceso_anterior: procesoAnterior?.descripcion,
                        avance_actual: avanceActual,
                        avance_anterior: avanceAnterior
                    });
                }

                //Verificar estados inválidos
                if (proceso.estado_proceso === 'COMPLETADO' && avanceActual < 100){
                    inconsistencias.push({
                        tipo: 'ESTADO_INVALIDO',
                        ot_codigo: ot.orden_trabajo_codigo_ot,
                        proceso: proceso.descripcion,
                        estado: proceso.estado_proceso,
                        avance: avanceActual
                    });
                }

                avanceAnterior = avanceActual;
                procesoAnterior = proceso;
            });
        });

        return inconsistencias;
    }
};

export default processCalculations;