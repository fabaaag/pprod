import { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { 
    updateItemRutaProgress,
    updateItemRutaEstado,
} from '../../../../api/programs.api';

export const useProcessProgress = (onProgressUpdated) => {
    const [loading, setLoading] = useState(false);
    const [selectedProcess, setSelectedProcess] = useState(null);
    const [selectedOtData, setSelectedOtData] = useState(null);

    // Actualizar progreso de un proceso
    const updateProgress = useCallback(async (itemRutaId, progressData) => {
        try {
            setLoading(true);
            const result = await updateItemRutaProgress(itemRutaId, {
                ...progressData,
                cantidad_completada: parseFloat(progressData.cantidad_completada)
            });

            //Notificar éxito según el resultado
            if (result.es_ultimo_proceso_ot && result.porcentaje_completado >= 100){
                toast.success(`¡Proceso completado! ${result.orden_trabajo?.codigo_ot || ''}`);
            } else {
                toast.success('Progreso actualizado correctamente');
            }

            onProgressUpdated?.(result);
            return result;
        } catch(error){
            console.error('Error actualizado progreso:', error);
            toast.error('Error al actualizar el progreso');
            throw error;
        } finally {
            setLoading(false);
        }
    }, [onProgressUpdated]);

    // Actualizar estado de un proceso
    const updateState = useCallback(async (itemRutaId, nuevoEstado) => {
        try {
            setLoading(true);
            const result = await updateItemRutaEstado(itemRutaId, nuevoEstado);

            // Mostrar mensaje según el estado
            const estadoTexto = {
                'PENDIENTE': '🔵 Pendiente',
                'EN_PROCESO': '🟡 En Proceso',
                'COMPLETADO': '🟢 Completado',
                'PAUSADO': '🟠 Pausado',
                'CANCELADO': '🔴 Cancelado'
            };

            toast.success(`Estado actualizado a ${estadoTexto[nuevoEstado]}`);

            // Mostrar sugerencias específicas según el estado
            if (nuevoEstado === 'EN_PROCESO'){
                setTimeout(() => {
                    toast('💡 Proceso iniciado. Registre el progreso usando el botón "📊 Progreso"', {
                        icon: '💡',
                        duration: 4000,
                        style: {
                            borderRadius: '10px',
                            background: '#e8f5e8',
                            color: '#2d5a2d',
                        },
                    });
                }, 1000);
            } else if (nuevoEstado === 'COMPLETADO') {
                toast('✅ ¡Proceso completado! Se actualizó automáticamente la cantidad terminada', {
                    icon: '✅',
                    duration: 3000,
                    style: {
                        background: '#d1f2eb',
                        color: '#0c5d56',
                    },
                });
            } else if (nuevoEstado === 'PAUSADO') {
                toast('⏸️ Proceso pausado. Podrá reanudarlo cambiando el estado a "En Proceso"', {
                    icon: '⏸️',
                    duration: 3000,
                    style: {
                        background: '#fff3cd',
                        color: '#856404',
                    },
                });
            }
            onProgressUpdated?.(result);
            return result;
        } catch (error) {
            console.error('Error actualizando estado:', error);
            const errorMessage = error.response?.data?.error || error.message || 'Error desconocido';
            toast.error(`Error actualizado estado: ${errorMessage}`);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [onProgressUpdated]);

    //Resetear avance de un proceso
    const resetProgress = useCallback(async (itemRutaId) => {
        if (!window.confirm('¿Está seguro de resetear el avance de este proceso a 0?')){
            return;
        }
        try {
            setLoading(true);
            const result = await updateItemRutaProgress(itemRutaId, {
                cantidad_completada: 0,
                observaciones: 'Avance reseteado manualmente'
            });

            toast.success('Avance resetado correctamente');
            onProgressUpdated?.(result);
            return result;
        } catch (error) {
            console.error('Error reseteando avance:', error);
            toast.error('Error al resetear el avance');
            throw error;
        } finally {
            setLoading(false);
        }
    }, [onProgressUpdated]);

    // Seleccionar proceso para actualizar
    const selectProcess = useCallback((proceso, otData) => {
        setSelectedProcess(proceso);
        setSelectedOtData(otData);
    }, []);

    //Limpiar selección
    const clearSelection = useCallback(() => {
        setSelectedProcess(null);
        setSelectedOtData(null);
    }, []);

    return {
        loading,
        selectedProcess,
        selectedOtData,
        updateProgress,
        updateState,
        resetProgress,
        selectProcess,
        clearSelection
    };
}