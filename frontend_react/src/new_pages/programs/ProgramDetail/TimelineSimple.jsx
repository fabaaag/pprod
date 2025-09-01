import React, { useState, useEffect } from 'react';
import Timeline from 'react-calendar-timeline';
import 'react-calendar-timeline/dist/Timeline.scss';
import moment from 'moment';
import { getProgram } from '../../../../api/programs.api';

export const TimelineSimple = ({ programId }) => {
    const [groups, setGroups] = useState([]);
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!programId) return;

        const loadData = async () => {
            try {
                setLoading(true);
                console.log('🔄 Cargando timeline simple para programa:', programId);
                
                const response = await getProgram(programId);
                
                if (!response?.routes_data) {
                    console.error('❌ No hay datos de timeline');
                    return;
                }
                
                const { groups: backendGroups, items: backendItems } = response.routes_data;
                console.log('📊 Datos recibidos:', { 
                    groups: backendGroups?.length, 
                    items: backendItems?.length 
                });

                // PROCESAMIENTO SIMPLIFICADO
                const processedGroups = [];
                const processedItems = [];

                // 1. Crear grupos principales (OTs)
                backendGroups?.forEach(ot => {
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
                backendItems?.forEach(item => {
                    processedItems.push({
                        id: item.id,
                        group: item.proceso_id, // Usar directamente el proceso_id
                        title: item.name,
                        start_time: moment(item.start_time).toDate(),
                        end_time: moment(item.end_time).toDate(),
                        itemProps: {
                            style: {
                                backgroundColor: '#FFA726',
                                color: 'white',
                                borderRadius: '4px',
                                padding: '2px 6px',
                                fontSize: '12px'
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
                    primerItem: processedItems[0]
                });

                setGroups(processedGroups);
                setItems(processedItems);

            } catch (error) {
                console.error('❌ Error cargando timeline:', error);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [programId]);

    if (loading) {
        return <div>Cargando timeline...</div>;
    }

    if (groups.length === 0 || items.length === 0) {
        return <div>No hay datos para mostrar</div>;
    }

    return (
        <div style={{ height: '600px', border: '1px solid #ccc' }}>
            <h4>Timeline Simple</h4>
            <Timeline
                groups={groups}
                items={items}
                defaultTimeStart={moment().startOf('day').toDate()}
                defaultTimeEnd={moment().add(7, 'days').endOf('day').toDate()}
                lineHeight={50}
                sidebarWidth={200}
                canMove={false}
                canResize={false}
                stackItems
            />
        </div>
    );
}; 