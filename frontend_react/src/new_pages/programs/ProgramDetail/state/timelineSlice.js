import { useState, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { getProgram } from '../../../../api/programs.api';
import moment from 'moment';
import tinycolor from 'tinycolor2';

const TIMELINE_COLORS = [
    '#FF9800', '#2196F3', '#4CAF50', '#9C27B0',
    '#E91E63', '#00BCD4', '#009688', '#FFC107'
];

const getColorForOT = (otId) => {
    const index = Math.abs(otId.split('_')[1]) % TIMELINE_COLORS.length;
    return TIMELINE_COLORS[index];
};


export const useTimelineState = (programId) => {
    const [timelineItems, setTimelineItems] = useState([]);
    const [timelineGroups, setTimelineGroups] = useState([]);
    const [timelineMode, setTimelineMode] = useState('planning');
    const [showTimeline, setShowTimeline] = useState(false);
    const [timelineLoading, setTimelineLoading] = useState(false);

    // SOLUCIÓN ALTERNATIVA: Procesamiento simplificado
    const loadTimelineData = useCallback(async () => {
        if (!programId) return;

        try {
            setTimelineLoading(true);
            console.log('🔄 Cargando timeline para programa:', programId);

            const response = await getProgram(programId);
            
            if (!response?.routes_data) {
                console.error('❌ No hay datos de timeline');
                return;
            }
            
            const { groups, items } = response.routes_data;
            console.log('📊a Datos recibidos:', { groups: groups, items: items });

            // PROCESAMIENTO SIMPLIFICADO
            const processedGroups = [];
            const processedItems = [];

            // 1. Crear grupos principales (OTs)
            groups?.forEach(ot => {
                processedGroups.push({
                    id: ot.id,
                    title: `OT ${ot.orden_trabajo_codigo_ot}`,
                    stackItems: true,
                    height: 70
                });

                // 2. Crear subgrupos (procesos) para cada OT
                ot.procesos?.forEach(proceso => {
                    processedGroups.push({
                        id: proceso.id,
                        title: proceso.descripcion,
                        parent: ot.id,
                        height: 50
                    });
                });
            });

            // 3. Procesar items directamente
            items?.forEach(item => {
                const otId = `ot_${item.ot_codigo || Math.floor(Math.random() * 1000)}`;
                const baseColor = getColorForOT(otId);
                const borderColor = tinycolor(baseColor).darken(10).toString();
                
                //Convertir las fechas string a objetos Date
                const startDate = moment(item.start_time).isValid()
                    ? moment(item.start_time)
                        .set('hour', Math.max(8, moment(item.start_time).hour()))
                        .set('minute', 0)
                        .toDate()
                    : moment().set('hour', 8).set('minute', 0).toDate();

                const endDate = moment(item.end_time).isValid()
                    ? moment(item.end_time).toDate()
                    : moment(startDate).add(1, 'hour').toDate(); 


                processedItems.push({
                    id: item.id,
                    group: item.proceso_id, // Usar directamente el proceso_id
                    title: item.name,
                    start: startDate,
                    end: endDate,
                    ot_codigo: item.ot_codigo,
                    color: baseColor,
                    borderColor: borderColor,
                    textColor: 'white',
                    proceso_codigo: item.proceso_codigo,
                    proceso_descripcion: item.proceso_descripcion,
                    producto: item.ot_descripcion,
                    cantidad_intervalo: item.cantidad_intervalo,
                    cantidad_total: item.cantidad_total,
                    cantidad_restante: item.cantidad_restante,
                    cantidad_completado: item.cantidad_terminada,
                    porcentaje_avance: item.cantidad_restante / item.cantidad_total * 100,
                    codigo_maquina: item.maquina_codigo,
                    maquina: item.maquina,
                    estandar: item.estandar,
                    operador: item.operador_nombre,

                    itemProps: {
                        style: {
                            backgroundColor: baseColor,
                            color: 'white',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            fontSize: '12px',
                            border: `2px solid ${borderColor}`,
                            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.12)'
                        },
                        'data-tooltip': `
                            ${item.name}
                            Cantidad: ${item.cantidad_intervalo} de ${item.cantidad_total}
                            Inicio: ${moment(item.start_time).format('DD/MM/YYYY HH:mm')}
                            Fin: ${moment(item.end_time).format('DD/MM/YYYY HH:mm')}
                        `
                    }
                });
            });

            console.log('✅ Procesamiento completado:', {
                grupos: processedGroups.length,
                items: processedItems.length,
                primerGrupo: processedGroups[0],
                primerItem: processedItems[0],
                items: processedItems.map(i => ({
                    id: i.id,
                    title: i.title,
                    start: i.start,
                    end: i.end
                }))
            });

            setTimelineGroups(processedGroups);
            setTimelineItems(processedItems);
            console.log('Items del timeline desde timelineSlice: ', processedItems);

        } catch (error) {
            console.error('❌ Error cargando timeline:', error);
            toast.error('Error al cargar la proyección');
        } finally {
            setTimelineLoading(false);
        }
    }, [programId]);

    const toggleTimeline = useCallback(() => {
        if (!showTimeline) {
            setTimelineLoading(true);
            loadTimelineData().then(() => {
                setShowTimeline(true);
            }).catch(error => {
                console.error("Error al cargar timeline:", error);
                toast.error("Error al cargar la proyección");
            }).finally(() => {
                setTimelineLoading(false);
            });
        } else {
            setShowTimeline(false);
        }
    }, [loadTimelineData, showTimeline]);

    const validateTimelineDisplay = useCallback((procesos) => {
        if (!procesos || procesos.length === 0) return false;
        
        const procesosConEstandarCero = procesos.filter(p => 
            !p.estandar || parseFloat(p.estandar) === 0
        );
        
        return procesosConEstandarCero.length === 0;
    }, []);

    return {
        timelineItems,
        timelineGroups,
        timelineMode,
        showTimeline,
        timelineLoading,
        loadTimelineData,
        setTimelineMode,
        toggleTimeline,
        validateTimelineDisplay
    };

    console.log(timelineItems, 'programslicer timelineItems');
};