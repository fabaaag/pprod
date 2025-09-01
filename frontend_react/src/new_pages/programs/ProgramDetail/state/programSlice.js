import { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { getProgram, cargarEstandarInicial, updateProductStandard, updateItemRutaStates } from '../../../../api/programs.api';
import { processCalculations } from '../utils/processCalculations';
import { getEstandaresProceso } from '../../../../api/productos.api';

export const useProgramState = (programId) => {
    const [programData, setProgramData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [otList, setOtList] = useState([]);
    const [metricas, setMetricas] = useState({
        totalKilosPlanificados: 0,
        totalKilosFabricados: 0,
        totalProcesos: 0,
        procesosCompletados: 0,
        procesosEnProceso: 0,
        procesosPendientes: 0,
        eficienciaPromedio: 0
    });

    // Cargar datos del programa
    const loadProgramData = useCallback(async () => {
        // ✅ Validación mejorada
        if (!programId || programId === 'undefined' || programId === '[object Object]') {
            console.error('ProgramId inválido:', programId);
            setLoading(false);
            return;
        }

        try {
            await updateItemRutaStates(programId);
            setLoading(true);
            console.log('Cargando programa con ID:', programId); // Para debug
            const response = await getProgram(programId);

            setProgramData({
                ...(response.program || {}),
                routes_data: response.routes_data
            });
            /**
             * Cargar estándares desde la api de productos
             * y actualizar los estándares de las OT, obviamente si el 
             * producto tiene estandar definido osease != 0
             */
            
            const ordenesTrabajo = response.ordenes_trabajo || [];
            setOtList(ordenesTrabajo);
            console.log('Órdenes de trabajo cargadas:', ordenesTrabajo); // Para debugS
            /*const estandares = handleUpdateInitialEstandar();
            console.log('inicializando estándares almacenados: ', estandares);*/

            //Calcular métricas
            const nuevasMetricas = processCalculations.calcularMetricas(ordenesTrabajo);
            setMetricas(nuevasMetricas);

            setTimeout(async () => {
                handleUpdateInitialEstandar(ordenesTrabajo)
                .then(cantidadActualizaciones => {
                    if (cantidadActualizaciones > 0) {
                        const metricasActualizadas = processCalculations.calcularMetricas(otList);
                        setMetricas(metricasActualizadas);
                    }
                })
                .catch(err => console.warn('Error en la actualización de estándares: ', err));
            }, 500);

        } catch (error) {
            console.error('Error cargando datos del programa:', error);
            toast.error('Error al cargar los datos del programa');
        } finally {
            setLoading(false);
        }
    }, [programId]);

    const handleUpdateInitialEstandar = useCallback(async (ordenesTrabajo = null) => {
        try {

            const ot_list = ordenesTrabajo || otList
            console.log('Iniciando actualización de estándares guardados...');
            console.log(`OTs disponibles: ${ot_list.length}`);

            if(!ot_list || ot_list.length === 0){
                console.warn('No hay OTs disponibles para actualizar');
                return 0;
            }
            
            //Contadores para tracking
            let otActualizadas = 0;
            let bdActualizadas = 0;
            

            //Iniciar todas las actualizaciones como promesas
            const actualizacionesPromises = ot_list.map(async (ot, index) => {
                //console.log(`OTOTOTOTOTO: ${JSON.stringify(ot)}`)
                //console.log(`Procesando OT ${index+1}/${ot_list.length}: ${ot.orden_trabajo_codigo_producto_salida || 'Sin código'} (${ot.orden_trabajo_descripcion_producto_ot || 'Sin descripción'})`)
                
                if (!ot.orden_trabajo_codigo_producto_salida || !ot.procesos?.length){
                    console.log(`⚠️ OT ${index+1} - Sin código de producto o sin procesos, omitiendo...`);
                    return ot;
                }

                //Para cada proceso, cargar su estandar si tiene máquina asignada
                const procesosActualizadosPromises = ot.procesos.map(async (proceso, pIndex) => {
                    //console.log(`  📊 Revisando proceso ${pIndex+1}/${ot.procesos.length}: ${proceso?.descripcion || 'Sin descripción'}`);
                    if (proceso?.maquina_id &&
                        (!proceso.estandar || parseFloat(proceso.estandar) === 0) &&
                        proceso?.proceso_id) {
                        console.log(`    ✅ Proceso ${pIndex+1} elegible para actualización:
                        - Máquina: ${proceso.maquina_id} (${proceso.maquina_descripcion || 'Sin descripción'})
                        - Proceso ID: ${proceso.proceso_id}
                        - Estándar actual: ${proceso.estandar || 0}`);
                        
                        try {
                            console.log(`    🔄 Solicitando estándar para OT:${ot.orden_trabajo}, Proceso:${proceso.proceso_id}, Máquina:${proceso.maquina_id}`);
                            const estandarBD = await cargarEstandarInicial(
                                programId,
                                ot.orden_trabajo,
                                proceso.proceso_id,
                                proceso.maquina_id
                            );
                            const estandarOT = proceso.estandar || 0;
                            console.log(`    📊 Respuesta de API: ${JSON.stringify(estandarBD?.estandar || 'No encontrado')}`);

                            // CASO 1: La OT no tiene estándar, pero hay uno en la BD de producto/pieza
                            if ((!estandarOT || estandarOT === 0) && estandarBD?.estandar && estandarBD.estandar > 0){
                                console.log(`    ✅ ACTUALIZANDO OT: Estándar ${estandarBD.estandar} para proceso ${proceso.proceso.id}`);
                                otActualizadas++;
                                return { ...proceso, estandar: estandarBD.estandar };
                            }
                            // CASO 2: El estándar en la BD es mayor que en la OT
                            else if (estandarBD?.estandar && estandarBD.estandar > 0 && estandarBD.estandar > estandarOT) {
                                console.log(`    ✅ ACTUALIZANDO OT: Estándar en BD ${estandarBD.estandar} es mayor que en OT ${estandarOT}`);
                                otActualizadas++;
                                return { ...proceso, estandar: estandarBD.estandar };
                            }

                        } catch (err) {
                            console.warn(`Error al cargar estándar para proceso ${proceso.id}: `, err);
                        }
                    } else {
                        /*console.log(`    ⏭️ Proceso ${pIndex+1} no requiere actualización:
                        - Tiene máquina: ${proceso?.maquina_id ? 'Sí' : 'No'}
                        - Tiene estándar: ${proceso.estandar ? 'Sí' : 'No'} (${proceso.estandar || 0})
                        - Tiene proceso ID: ${proceso?.proceso_id ? 'Sí' : 'No'}`);*/
                    }
                    return proceso; //Si no cumple condiciones o hay error, devuelve el proceso solo
                });

                //ESperar a que se resuelvan todas las promesas de procesos
                const procesosActualizados = await Promise.all(procesosActualizadosPromises);

                //Verificar si hubo cambios en los estándares
                const huboActualizaciones = procesosActualizados.some(
                    (procesosActualizado, idx) => 
                        procesosActualizado.estandar !== ot.procesos[idx].estandar
                );

                console.log(`🔄 OT ${index+1} procesada - Hubo actualizaciones: ${huboActualizaciones ? 'SÍ' : 'NO'}`);
                //Devolver ot con procesos actualizados
                return {
                    ...ot,
                    procesos: procesosActualizados,
                    _actualizaciones: huboActualizaciones
                };
            });

            //Esperar a que todas las ots sean procesadas
            const otListActualizada = await Promise.all(actualizacionesPromises)

            //Contar cuántos estándares se actualizaron
            const cantidadActualizaciones = otListActualizada.reduce(
                (total, ot) => ot._actualizaciones ? total + 1 : total, 0
            )

            console.log(`📊 RESUMEN DE ACTUALIZACIÓN:
            - OTs procesadas: ${otListActualizada.length}
            - OTs con actualizaciones: ${cantidadActualizaciones}
            - Éxito: ${cantidadActualizaciones > 0 ? 'SÍ' : 'NO'}`);
            

            //Actualizar el estado solo si hay cambios
            if (cantidadActualizaciones > 0){
                console.log('Actualizando estado con nuevos estándares...');
                setOtList(otListActualizada.map(({ _actualizaciones, ...ot }) => ot));
                toast.success(`Se aplicaron ${cantidadActualizaciones} estándares guardados`);
                return cantidadActualizaciones;
            }
            return 0; 

        } catch (error) {
            console.error('Error al actualizar estándares:', error);
            console.error('stack trace:', error.stack);
            toast.error('Error al cargar estándares guardados');
            return 0;
        }
    }, [programId, otList]);

    // Actualizar orden de trabajo
    const updateOT = useCallback((otId, updates) => {
        setOtList(prevList => 
            prevList.map(ot => 
                ot.orden_trabajo === otId ? { ...ot, ...updates } : ot
            )
        );
    }, []);

    //Eliminar orden de trabajo
    const removeOT = useCallback((otId) => {
        setOtList(prevList => 
            prevList.filter(ot => ot.orden_trabajo !== otId)
        );
    }, []);

    //Actualizar proceso
    const updateProceso = useCallback((otId, procesoId, updates) => {
        setOtList(prevList => 
            prevList.map(ot => {
                if (ot.orden_trabajo === otId) {
                    return {
                        ...ot,
                        procesos: ot.procesos.map(proceso => 
                            proceso.id === procesoId ? {...proceso, ...updates } : proceso
                        )
                    };
                }
                return ot;
            })
        );
    }, []);

    //Verificar inconsistencias
    const checkInconsistencias = useCallback(() => {
        return processCalculations.verificarInconsistencias(otList);
    }, [otList]);

    //Verificar estándares en cero
    const checkEstandaresCero = useCallback(() => {
        return processCalculations.verificarEstandaresCero(otList);
    }, [otList]);

    return {
        programData,
        loading,
        otList,
        metricas,
        loadProgramData,
        updateOT,
        removeOT,
        updateProceso,
        checkInconsistencias,
        checkEstandaresCero,
        cargarEstandaresGuardados: handleUpdateInitialEstandar
    };

}