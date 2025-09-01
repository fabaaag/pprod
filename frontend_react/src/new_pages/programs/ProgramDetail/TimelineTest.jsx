import React, { useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { getProgram } from '../../../../api/programs.api';

const localizer = momentLocalizer(moment);

export const TimelineTest = ({ programId }) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!programId) return;

        const loadData = async () => {
            try {
                setLoading(true);
                console.log('🔄 Cargando timeline de prueba para programa:', programId);
                
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

                // PROCESAMIENTO PARA REACT-BIG-CALENDAR
                const processedEvents = [];

                backendItems?.forEach(item => {
                    // Buscar información del proceso
                    const proceso = backendGroups
                        ?.flatMap(ot => ot.procesos || [])
                        ?.find(p => p.id === item.proceso_id);

                    // Buscar información de la OT
                    const ot = backendGroups?.find(g => g.id === item.ot_id);

                    const event = {
                        id: item.id,
                        title: `${item.name} (${ot?.orden_trabajo_codigo_ot || 'OT'})`,
                        start: moment(item.start_time).toDate(),
                        end: moment(item.end_time).toDate(),
                        resource: {
                            proceso: proceso?.descripcion || 'Sin descripción',
                            ot: ot?.orden_trabajo_codigo_ot || 'OT',
                            cantidad: item.cantidad_intervalo,
                            total: item.cantidad_total,
                            estado: item.estado || 'PENDIENTE'
                        },
                        backgroundColor: '#FFA726',
                        borderColor: '#E65100',
                        textColor: '#ffffff'
                    };

                    processedEvents.push(event);
                });

                console.log('✅ Procesamiento completado:', {
                    eventos: processedEvents.length,
                    primerEvento: processedEvents[0]
                });

                setEvents(processedEvents);

            } catch (error) {
                console.error('❌ Error cargando timeline:', error);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, [programId]);

    const eventStyleGetter = (event) => {
        return {
            style: {
                backgroundColor: event.backgroundColor,
                borderColor: event.borderColor,
                color: event.textColor,
                borderRadius: '4px',
                border: '2px solid',
                padding: '2px 4px',
                fontSize: '11px'
            }
        };
    };

    if (loading) {
        return <div>Cargando timeline...</div>;
    }

    if (events.length === 0) {
        return <div>No hay datos para mostrar</div>;
    }

    return (
        <div style={{ height: '600px', border: '1px solid #ccc' }}>
            <h4>Timeline de Prueba</h4>
            <Calendar
                localizer={localizer}
                events={events}
                startAccessor="start"
                endAccessor="end"
                style={{ height: '500px' }}
                defaultView="week"
                views={['day', 'week', 'month']}
                step={0}
                timeslots={1}
                eventPropGetter={eventStyleGetter}
                selectable={false}
                popup={true}
                onSelectEvent={(event) => {
                    console.log('Evento seleccionado:', event);
                }}
            />
        </div>
    );
}; 