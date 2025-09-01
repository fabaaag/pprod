import { useState, useCallback, useEffect } from 'react';
import moment from 'moment';
import { getProgram, getProgramTimelineEjecucion, getProgramTimelinePlanning } from '../../../../api/programs.api';
import { toast } from 'react-hot-toast';
import timelineHelpers from '../utils/timelineHelpers';

//Helpers para colores y tooltips (ni pta idea q es esto)
const getEventColor = (estado, mode) => {
    if (mode === 'execution') {
        switch (estado?.toUpperCase()) {
            case 'COMPLETADO' : return '#4CAF50'; 
            case 'EN_PROCESO' : return '#2196F3';
            case 'DETENIDO' : return '#F44336';
            default: return '#9E9E9E';
        }
    } else {
        return '#FFA826'; 
    }
};

const getEventBorderColor = (estado) => {
    switch (estado?.toUpperCase()){
        case 'COMPLETADO' : return '#2E7D32';
        case 'EN_PROCESO' : return '#1565C0';
        case 'DETENIDO' : return '#C62828';
        default: return '#E65100';
    }
};

const buildTooltip = (item, ot, proceso) => `
    <strong>${item.name}</strong><br />
    <strong>OT: </strong>${item.ot_codigo || ot?.orden_trabajo_codigo_ot || 'N/A'}<br />
    <strong>Producto: </strong>${item.ot_descripcion || ot?.orden_trabajo_descripcion || 'N/A'}<br />
    <strong>Cantidad: </strong>${item.cantidad_intervalo} de ${item.cantidad_total}<br />
    <strong>Estado: </strong>${item.estado || 'PENDIENTE'}<br />
    <strong>Máquina: </strong>${item.maquina_codigo || item.maquina || 'Sin asignar'}<br />
    <strong>Operador: </strong>${item.operador_nombre || 'Sin asignar'}<br />
    <strong>Inicio: </strong>${moment(item.start_time).format('DD/MM/YYYY HH:MM')}<br />
    <strong>Fin: </strong>${moment(item.end_time).format('DD/MM/YYYY HH:mm')}<br />
    ${item.porcentaje_avance ? `<br /><strong>Avance: </strong> ${item.porcentaje_avance.toFixed(1)}%`: ''}
    ${item.es_bloque_unificado ? `<br /><strong>Bloque: </strong>${item.periodo || 'Unificado'}<br />` : ''}
    ${item.observaciones ? `<strong>Obs: </strong>${item.observaciones}<br />`: ''}
    <strong>Bloque: </strong><br />
`;


export const useTimeline = (programId) => {
    const [timelineItems, setTimelineItems]  = useState([]);
    const [timelineGroups, setTimelineGroups] = useState([]);
    const [timelineMode, setTimelineMode] = useState('planning');
    const [showTimeline, setShowTimeline] = useState(false);
    const [timelineLoading, setTimelineLoading] = useState(false);
    const [timeRange, setTimeRange] = useState({
        start: moment().startOf('day').toDate(),
        end: moment().add(14, 'days').endOf('day').toDate()
    });

    // Procesamiento avanzado de datos
    const processTimelineData = useCallback((timelineData)=> {
        if (!timelineData || !timelineData.groups || !timelineData.items ){
            return { processedGroups: [], processedItems: []};
        }

        // Procesar grupos (OTs y procesos)
        let processedGroups = [];
        timelineData.groups.forEach(ot => {
            processedGroups.push({
                id: ot.id,
                title: typeof ot.orden_trabajo_codigo_ot === 'number'
                    ? `OT ${ot.orden_trabajo_codigo_ot}`
                    : ot.orden_trabajo_codigo_ot || `OT ${ot.id}`,
                stackItems: true,
                height: 70
            });
            if (ot.procesos && Array.isArray(ot.procesos)){
                ot.procesos.forEach(proceso => {
                    processedGroups.push({
                        id: proceso.id,
                        title: proceso.descripcion,
                        parent: ot.id,
                        height: 50,
                    });
                });
            }
        });

        // Procesar items con enriquecimiento avanzado
        const processedItems = timelineData.items.map(item => {
            const proceso = timelineData.groups
                ?.flatMap(ot => ot.procesos || [])
                .find(p => p.id === item.proceso_id) || {};
            const ot = timelineData.groups?.find(g => g.id === item.ot_id);

            return {
                id: item.id,
                title: item.title || item.name || 'Sin título',
                start: moment(item.start_time).toDate(),
                end: moment(item.end_time).toDate(),
                backgroundColor: getEventColor(item.estado, timelineMode),
                borderColor: getEventBorderColor(item.estado),
                textColor: '#ffffff',
                resource: {
                    proceso: item.proceso_descripcion || proceso?.descripcion || 'Sin descripción',
                    ot: item.ot_codigo || ot?.orden_trabajo_codigo_ot || 'OT',
                    cantidad: item.cantidad_intervalo || 0,
                    total: item.cantidad_total || 0,
                    estado: item.estado || 'PENDIENTE',
                    maquina: item.maquina_codigo || item.maquina || 'Sin máquina',
                    operador: item.operador_nombre || 'Sin operador',
                    maquina_descripcion: item.maquina_descripcion || '',
                    operador_id: item.operador_id || null,
                    proceso_id: item.proceso_id,
                    ot_id: item.ot_id,
                    cantidad_terminado: item.cantidad_terminada || 0,
                    porcentaje_avance: item.porcentaje_avance || 0,
                    fecha_inicio_real: item.fecha_inicio_real,
                    fecha_fin_real: item.fecha_fin_real,
                    observaciones: item.observaciones || '',
                    es_bloque_unificado: item.es_bloque_unificado || false,
                    periodo: item.periodo || '',
                    ot_descripcion: item.ot_descripcion || ot?.orden_trabajo_descripcion_producto_ot || '',
                    ot_fecha_termino: item.ot_fecha_termino || ot?.orden_trabajo_fecha_termino || '',
                    proceso_codigo: item.proceso_codigo || proceso?.codigo_proceso || ''
                },
                tooltip: buildTooltip(item, ot, proceso),
            };
        });
        return { processedGroups, processedItems };
    }, [timelineMode]);

    //Cargar datos del timeline
    const loadTimelineData = useCallback(async () => {
        if (!showTimeline || !programId) return;

        try {
            setTimelineLoading(true);
            let timelineData;

            if (timelineMode === 'execution'){
                const response = await getProgramTimelineEjecucion(programId);
                timelineData = response || { groups: [], items: [] };
            } else {
                const response = await getProgram(programId);
                timelineData = response?.routes_data || { groups: [], items: [] };
            }

            const { processedGroups, processedItems } = processTimelineData(timelineData);
            console.log('📊a Datos procesados:', { groups: processedGroups, items: processedItems });
            setTimelineGroups(processedGroups);
            setTimelineItems(processedItems);
        } catch (error) {
            toast.error('Error al cargar la línea de tiempo');
        } finally {
            setTimelineLoading(false);
        }
    }, [programId, showTimeline, timelineMode, processTimelineData]);

    // Validar si se puede mostrar el timeline
    const validateTimelineDisplay = useCallback((procesos) => {
        if (!procesos || procesos.length === 0) return false;
        const procesosConEstandarCero = procesos.filter(p => !p.estandar === 0);
        return procesosConEstandarCero.length === 0;
    }, []);

    // Cambiar modo del timeline
    const setMode = useCallback((mode) => {
        setTimelineMode(mode);
    }, []);

    //Mostrar/ocultar timeline
    const toggleTimeline = useCallback((procesos = [] ) => {
        const newState = !showTimeline;
        setShowTimeline(newState);
        if (newState && procesos.length > 0) {
            const isValid = validateTimelineDisplay(procesos);
            if (!isValid) {
                toast.error('No se puede mostrar el timeline: hay procesos con estándar 0')
                setShowTimeline(false);
                return;
            }
        }
    }, [showTimeline, validateTimelineDisplay]);

    useEffect(() => {
        if (showTimeline) {
            loadTimelineData();
        }
    }, [showTimeline, timelineMode, loadTimelineData]);

    return {
        timelineItems,
        timelineGroups,
        timelineMode,
        showTimeline,
        timelineLoading,
        timeRange,
        setTimelineMode: setMode,
        toggleTimeline,
        validateTimelineDisplay,
        loadTimelineData
    };
};