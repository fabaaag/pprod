import moment from 'moment';

export const timelineUtils = {
    /**
     * Procesa los grupos para el timeline
     */

    processGroups: (groups) => {
        if(!Array.isArray(groups)) return [];

        return groups.flatMap(ot => {
            //Grupo principal (OT)
            const mainGroup = {
                id: ot.id,
                title: ot.orden_trabajo_codigo_ot || 'OT Sin código',
                stackItems: true,
                height: 70
            };

            //Subgrupos (procesos)
            const processGroups = ot.procesos?.map(proceso => ({
                id:`${ot.id}-${proceso.id}`,
                title: proceso.descripcion || 'Sin descripción',
                height: 50,
                parent: ot.id,
            })) || [];

            return [mainGroup, ...processGroups];
        });
    },
    /**
     * Procesa los items para el timeline
     */
    processItems: (items, mode='planning') => {
        if(!Array.isArray(items)) return [];

        return items.map(item => ({
            id: item.id,
            group: item.group,
            title:item.title || 'Sin título',
            start_time: moment(item.start_time),
            end_time: moment(item.end_time),
            itemProps: {
                style: {
                    background: mode === 'execution' ? 
                    timelineUtils.getExecutionColor(item.estado) :
                    timelineUtils.getPlanningColor(item.tipo),
                    color: '#fff'
                },
                'data-tooltip': `${item.title}\nInicio: ${moment(item.start_time).format('DD/MM/YYY HH:mm')}\nFin: ${moment(item.end_time).format('DD/MM/YYYY HH:mm ')}`
                },
                porcentaje_avance: item.porcentaje_avance
        }));
    },

    /**
     * Obtiene el color según el estado de ejecución
     */
    getExecutionColor: (estado) => {
        switch(estado?.toUpperCase()){
            case 'COMPLETADO': return '#4CAF50';
            case 'EN_PROCESO': return '#2196F3';
            case 'DETENIDO': return '#f44336';
            default: return '#FFA726'
        }
    },

    /**
     * Obtiene el color según el tipo de planificación
     */
    getPlanningColor: (tipo) => {
        switch(tipo?.toUpperCase()){
            case 'PROCESO': return '#1976D2';
            case 'SETUP': return '#FFA000';
            case 'MANTENIMIENTO': return '#D32F2F';
            default: return '#757575'
        }
    },

    /**
     * Verifica si hay procesos con estándar en cero
     */
    checkZeroStandardProcesses: (otList) => {
        if(!Array.isArray(otList)) return false;

        return otList.some(ot =>
            ot.procesos?.some(proceso => 
                !proceso.estandar_proceso || proceso.estandar_proceso <= 0
            )
        );
    },

    /**
     * Obtiene los procesos con estándar en 0
    */
    getZeroStandardProcesses: (otList) => {
        if (!Array.isArray(otList)) return [];

        return otList.reduce((acc, ot) => {
            const procesosConEstandarCero = ot.procesos?.filter(proceso => 
                !proceso.estandar_proceso || proceso.estandar_proceso <= 0
            ) || [];

            return [...acc, ...procesosConEstandarCero.map(proceso => ({
                ot_codigo: ot.orden_trabajo_codigo_ot,
                proceso_descripcion: proceso.descripcion
            }))];
        }, []);
    }
};
export default timelineUtils;