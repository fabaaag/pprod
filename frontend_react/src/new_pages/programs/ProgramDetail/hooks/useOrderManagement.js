import { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { 
    addOrdersToProgram,
    deleteOrder, 
    updatePriorities,
    getUnassignedOrders,
} from '../../../../api/programs.api';

export const useOrderManagement = (programId, onOrdersUpdated) => {
    const [loading, setLoading] = useState(false);
    const [orders, setOrders] = useState([]);
    const [availableOrders, setAvailableOrders] = useState([]);
    const [showAddOrderModal, setShowAddOrderModal] = useState(false);

    const aplicarEstandaresGuardados = async(nuevasOTs) => {
        try {
            if (!nuevasOTs || nuevasOTs.length === 0) return nuevasOTs;

            //Registro total de estándares aplicados
            let contadorEstandaresAplicados = 0;

            const promesasEstandares = [];

            const otsConEstandares = await Promise.all(
                nuevasOTs.map(async (ot) => {
                    if (!ot.procesos || ot.procesos.length === 0) return ot;

                    const proceesosActualizados = await Promise.all(
                        ot.procesos.map(async (proceso) => {
                            if (
                                proceso.maquina_id && 
                                (!proceso.estandar || parseFloat(proceso.estandar) === 0) &&
                                proceso.proceso_id
                            ) {
                                try {
                                    //Buscar estándares usando el código de producto 

                                    const codigoProducto = ot.codigo_producto_salida;

                                    if (codigoProducto){
                                        const data = await getEstandaresProceso(
                                            proceso.proceso_id,
                                            'producto',
                                            codigoProducto
                                        );
                                        
                                        if(data && data.maquinas_compatibles) {
                                            const maquinaConEstandar = data.maquinas_compatibles.find(
                                                m => m.id == proceso.maquina_id && m.estandar > 0
                                            );
                                            
                                            if (maquinaConEstandar){
                                                contadorEstandaresAplicados++;
                                                return {
                                                    ...proceso,
                                                    estandar: maquinaConEstandar.estandar
                                                };
                                            }

                                        }
                                    }
                                } catch (error) {
                                    console.error('Error buscando estándares:', error);
                                }
                            }
                            return proceso;
                        })
                    );

                    return {
                        ...ot,
                        procesos: proceesosActualizados
                    };
                })
            );
        } catch (error){
            console.error('Error aplicando estándares guardados:', error);
            toast.error('Error al aplicar estándares guardados');
        }
    }

    //Cargar órdenes disponibles
    const loadAvailableOrders = useCallback(async () => {
        try {
            setLoading(true);
            const response = await getUnassignedOrders();
            setAvailableOrders(response.data);
            
        } catch (error) {
            console.error('Error cargando órdenes disponibles:', error);
            toast.error('Error al cargar órdenes disponibles');
        } finally {
            setLoading(false);
        }
    }, []);

    // Añadir órdenes al programa
    const addOrders = useCallback(async (orderIds) => {
        try {
            setLoading(true);
            await addOrdersToProgram(programId, orderIds);
            toast.success('Órdenes agregadas correctamente');
            onOrdersUpdated?.();
            setShowAddOrderModal(false);
        } catch (error) {
            console.error('Error agregando órdenes:', error);
            toast.error('Error al agregar órdenes');
            throw error;
        } finally {
            setLoading(false);
        }
    }, [programId, onOrdersUpdated]);

    // Eliminar orden del program
    const removeOrder = useCallback(async (orderId) => {
        if (!window.confirm('¿Está seguro que desea eliminar esta orden de trabajo?')){
            return;
        }

        try {
            setLoading(true);
            const result = await deleteOrder(orderId);

            if (result && result.deleted > 0){
                setOrders(prevOrders => prevOrders.filter(order => order.orden_trabajo !== orderId));
                toast.success('Orden eliminada correctamente');
                onOrdersUpdated?.();
            } else {
                throw new Error('No se pudo eliminar la orden');
            }
        } catch (error) {
            console.error('Error eliminando orden:', error);
            toast.error(error.message || 'Error al eliminar la orden');
            throw error;
        } finally {
            setLoading(false);
        }
    }, [programId, onOrdersUpdated]);

    // Actualizar prioridades de órdenes
    const updateOrderPriorities = useCallback(async (newOrderList) => {
        try {
            setLoading(true);
            console.log('Actualizando prioridades: ', newOrderList);

            setOrders(newOrderList);

            const updatedGroups = newOrderList.flatMap(ot => {
                const mainGroup = {
                    id: `ot_${ot.orden_trabajo}`,
                    title: ot.orden_trabajo_codigo_ot,
                    height: 50,
                    stackItems: true
                };

                const processGroups = ot.procesos?.map(proceso => ({
                    id: `${mainGroup.id}-${proceso.id}`,
                    title: proceso.descripcion,
                    parent: mainGroup.id,
                    height: 30
                })) || [];

                return [mainGroup, ...processGroups];
            });

            const orderIds = newOrderList.map((order, index) => ({
                id: order.orden_trabajo,
                priority: index + 1                
            })).filter(item => item !== null);
            console.log('Actualizando prioridades: ', orderIds);

            const response = await updatePriorities(programId, orderIds);
            console.log('Prioridades actualizadas:', response);

            // Procesar items del timeline si existe respuesta
            if (response.routes_data?.items){
                const serverItems = response.routes_data.items.map(item => ({
                    id: item.id,
                    group: `${item.ot_id}-${item.proceso_id}`,
                    title: `${item.name} (Restantes: ${item.unidades_restantes})`,
                    start_time: new Date(item.start_time + 'Z'),
                    end_time: new Date(item.end_time + 'Z'),
                    itemProps: {
                        style: {
                            backgroundColor: '#4CAF50',
                            color: 'white',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            opacity: 1 - (item.unidades_restantes / item.cantidad_total)
                        }
                    }
                }));

                //Notificar al componente padre con los nuevos datos
                onOrdersUpdated?.({
                    items: serverItems,
                    groups: updatedGroups
                });
            }
            toast.success('Prioridades actualizadas correctamente');
            
        } catch (error) {
            console.error('Error actualizando prioridades:', error);
            toast.error('Error al actualizar prioridades');
            throw error;
        } finally {
            setLoading(false);
        }
    }, [programId, onOrdersUpdated]);

    // Actualizar lista de órdenes
    const setOrderList = useCallback((newOrders) => {
        setOrders(newOrders);
    }, []);

    // Toggle modal de agregar órdenes
    const toggleAddOrderModal = useCallback(() => {
        const newState = !showAddOrderModal;
        setShowAddOrderModal(newState);
        if (newState) {
            loadAvailableOrders();
        }
    }, [showAddOrderModal, loadAvailableOrders]);

    return {
        loading,
        orders,
        availableOrders,
        showAddOrderModal,
        setOrderList,
        addOrders,
        removeOrder,
        updateOrderPriorities,
        toggleAddOrderModal
    };
};