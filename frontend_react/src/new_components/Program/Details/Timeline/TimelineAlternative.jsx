import React, { useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { getProgram } from '../../../../api/programs.api';
import { LoadingSpinner } from '../../../../components/UI/LoadingSpinner/LoadingSpinner';

const localizer = momentLocalizer(moment);

export const TimelineAlternative = ({ programId, timelineMode = 'planning' }) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!programId) return;

        const loadData = async () => {
            try {
                setLoading(true);
                console.log('🔄 Cargando timeline alternativo para programa:', programId);
                
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
                        backgroundColor: getEventColor(item.estado, timelineMode),
                        borderColor: getEventBorderColor(item.estado),
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
    }, [programId, timelineMode]);

    const getEventColor = (estado, mode) => {
        if (mode === 'execution') {
            switch (estado?.toUpperCase()) {
                case 'COMPLETADO': return '#4CAF50';
                case 'EN_PROCESO': return '#2196F3';
                case 'DETENIDO': return '#F44336';
                default: return '#9E9E9E';
            }
        } else {
            return '#FFA726'; // Naranja para planificación
        }
    };

    const getEventBorderColor = (estado) => {
        switch (estado?.toUpperCase()) {
            case 'COMPLETADO': return '#2E7D32';
            case 'EN_PROCESO': return '#1565C0';
            case 'DETENIDO': return '#C62828';
            default: return '#E65100';
        }
    };

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

    const tooltipAccessor = (event) => {
        return `
            ${event.title}
            Proceso: ${event.resource.proceso}
            Cantidad: ${event.resource.cantidad} de ${event.resource.total}
            Estado: ${event.resource.estado}
            Inicio: ${moment(event.start).format('DD/MM/YYYY HH:mm')}
            Fin: ${moment(event.end).format('DD/MM/YYYY HH:mm')}
        `;
    };

    if (loading) {
        return <LoadingSpinner message="Cargando proyección..." />;
    }

    if (events.length === 0) {
        return (
            <div className="text-center p-4">
                <p className="text-muted">No hay datos disponibles para mostrar en la línea de tiempo.</p>
            </div>
        );
    }

    // Calcular rango de fechas
    const startDate = moment.min(events.map(e => moment(e.start))).subtract(1, 'day').toDate();
    const endDate = moment.max(events.map(e => moment(e.end))).add(1, 'day').toDate();

    return (
        <div style={{ height: '600px', padding: '20px' }}>
            <div className="mb-3">
                <h5>Proyección Temporal - {timelineMode === 'planning' ? 'Planificación' : 'Ejecución'}</h5>
                <small className="text-muted">
                    {events.length} eventos programados
                </small>
            </div>
            
            <Calendar
                localizer={localizer}
                events={events}
                startAccessor="start"
                endAccessor="end"
                style={{ height: '500px' }}
                defaultDate={startDate}
                defaultView="week"
                views={['day', 'week', 'month']}
                step={60}
                timeslots={1}
                eventPropGetter={eventStyleGetter}
                tooltipAccessor={tooltipAccessor}
                selectable={false}
                popup={true}
                onSelectEvent={(event) => {
                    console.log('Evento seleccionado:', event);
                }}
                components={{
                    event: (props) => (
                        <div 
                            {...props}
                            title={tooltipAccessor(props.event)}
                            style={{
                                ...props.style,
                                padding: '2px 4px',
                                fontSize: '10px',
                                whiteSpace: 'nowrap',
                                overflow: 'visible',
                                textOverflow: 'ellipsis'
                            }}
                        >
                            {props.title}
                        </div>
                    )
                }}
            />
        </div>
    );
}; 