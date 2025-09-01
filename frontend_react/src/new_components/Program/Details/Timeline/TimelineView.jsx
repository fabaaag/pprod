import React, { useState } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { LoadingSpinner } from '../../../../components/UI/LoadingSpinner/LoadingSpinner';
import { Button, ButtonGroup, Badge } from 'react-bootstrap';
import { FaCalendarAlt, FaList, FaTable } from 'react-icons/fa';
import { EventDetailsModal } from '../Modals/EventDetailsModal';
import './TimelineView.css';
import tinycolor from 'tinycolor2';


/**
 * darle funcionalidad a los botones del timeline
 */

const localizer = momentLocalizer(moment);

export const TimelineView = ({
    timelineGroups,
    timelineItems,
    timelineMode,
    isLoading,
}) => {
    const [currentView, setCurrentView] = useState('week');
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [showEventModal, setShowEventModal] = useState(false);

    console.log("TimelineView props:", {
        timelineGroups,
        timelineItems,
        timelineMode,
        isLoading
    });

    //Estadisticas y rango de fechas
    const getProgramDateRange = () => {
        if (!timelineItems || timelineItems.length === 0) {
            return {
                start: moment().startOf('month').toDate(),
                end: moment().endOf('month').toDate()
            };
        }
        const startDate = moment.min(timelineItems.map(e => moment(e.start)));
        const endDate = moment.max(timelineItems.map(e => moment(e.end)));
        const marginDays = 2;
        return {
            start: startDate.subtract(marginDays, 'days').startOf('day').toDate(),
            end: endDate.add(marginDays, 'days').endOf('day').toDate()
        };
    };

    const getProgramStats = () => {
        if (!timelineItems || timelineItems.length === 0) return null;
        return {
            totalEvents: timelineItems.length,
            totalOTs: new Set(timelineItems.map(e => e.resource?.ot)).size,
            totalProcesos: new Set(timelineItems.map(e => e.resource?.proceso)).size,
            dateRange: {
                start: moment.min(timelineItems.map(e => moment(e.start))).format('DD/MM/YYYY'),
                end: moment.max(timelineItems.map(e => moment(e.end))).format('DD/MM/YYYY')
            },
            estados: timelineItems.reduce((acc, event) => {
                const estado = event.resource?.estado || 'PENDIENTE';
                acc[estado] = (acc[estado] || 0) + 1;
                return acc;
            }, {})
        };
    };

    if (isLoading) {
        return (
             <LoadingSpinner message='Cargando proyección...' />
        );
    }

    if (!timelineItems || timelineItems.length === 0) {
        return (
            <div className="timeline-empty-state">
                <p>No hay datos disponibles para mostrar en la linea de tiempo</p>
            </div>
        );
    }

    const stats = getProgramStats();
    const dateRange = getProgramDateRange();

    // Estilos y clases para eventos
    const eventStyleGetter = (event) => {
        let eventClass = 'event-pendiente';
        if (event.resource?.estado){
            switch (event.resource.estado.toUpperCase()){
                case 'COMPLETADO': eventClass = 'event-completado'; break;
                case 'EN_PROCESO': eventClass = 'event-en-proceso'; break;
                case 'DETENIDO': eventClass = 'event-detenido'; break;
                default: eventClass = 'event-pendiente';
            }
        }
        let additionalClasses = '';
        if (event.resource?.es_bloque_unificado) {
            additionalClasses += ' bloque-unificado';
            if (event.resource?.periodo) {
                if (event.resource.periodo.toLowerCase().includes('mañana')) {
                    additionalClasses += 'bloque-manana';
                } else if (event.resource.periodo.toLowerCase().includes('tarde')){
                    additionalClasses += ' bloque-tarde';
                }
            } 
        }

        const eventStart = moment(event.start);
        const eventHour = eventStart.hour();
        const isWorkingHour = eventHour >= 7 && eventHour < 19;
        if (isWorkingHour){
            additionalClasses += ' rbc-working-hour-event';
        }
        return {
            style: {
                backgroundColor: event.color,
                borderColor: event.borderColor,
                color: event.textColor,
                borderRadius: '6px',
                border: '2px solid',
                padding: '3px 6px',
                fontSize: '11px',
                fontWeight: 'bold'
            },
            className: `rbc-event ${eventClass}${additionalClasses}`
        };
    };

    return (
        <div className="timeline-container">
            {/*Header*/}
            <div className="timeline-header mb-3">
                <div className="d-flex justify content-between align-items-center">
                    <div>
                        <h5>Proyeccion Temporal - {timelineMode === 'planning' ? 'Planificación': 'Ejecución'}</h5>
                        {stats && (
                            <div className="d-flex gap-3 aling-items-center">
                                <Badge bg="primary">{stats.totalEvents} eventos</Badge>
                                <Badge bg="info">{stats.totalOTs} OTs</Badge>
                                <Badge bg="secondary">{stats.totalProcesos} procesos</Badge>
                                <small className="text-muted">
                                    {stats.dateRange.start} - {stats.dateRange.end}
                                </small>
                                <Badge className="ms" bg='success'>
                                   🕐 Horario: 8:00 - 17:30 (Viernes 16:30)
                                </Badge>

                            </div>
                        )}
                    </div>
                    
                    <div className="d-flex gap-2 align-items-right">
                        <ButtonGroup size='sm'>
                            <Button
                                variant={currentView === 'day' ? 'primary' : 'outline-primary'}
                                onClick={() => setCurrentView('day')}
                            >
                                <FaCalendarAlt className="me-1" />
                                Día 
                            </Button>
                            <Button
                                variant={currentView === 'week' ? 'primary' : 'outline-primary'}
                                onClick={() => setCurrentView('week')}
                            >
                                <FaCalendarAlt className="me-1" />
                                Semana 
                            </Button>
                            {/*<Button
                                variant={currentView === 'month' ? 'primary' : 'outline-primary'}
                                onClick={() => setCurrentView('month')}
                            >
                                <FaCalendarAlt className="me-1" />
                                Mes 
                            </Button>*/}
                        </ButtonGroup>
                        <Button
                            variant="outline-secondary"
                            size="sm"
                            onClick={() => setCurrentDate(new Date())}
                        >
                            Hoy
                        </Button>
                    </div>
                </div>
                {stats && stats.estados && (
                    <div className="mt-2">
                        <small className="text-muted">Estados: </small>
                        {Object.entries(stats.estados).map(([estado, count]) => (
                            <Badge
                                key={estado}
                                bg={estado === 'COMPLETADO' ? 'success' : 
                                    estado === 'EN_PROCESO' ? 'primary' : 'secondary'}
                                className="me-1"
                            >
                                {estado} : {count}
                            </Badge>
                        ))}
                    </div>
                )}
            </div>
            {/*Calendario */}
            <div className="timeline-calendar-container">
                <Calendar
                    localizer={localizer}
                    events={timelineItems}
                    startAccessor="start"
                    endAccessor="end"
                    style={{ height: '100%' }}
                    view={currentView}
                    onView={setCurrentView}
                    date={currentDate}
                    defaultDate={dateRange.start}
                    views={['day', 'week', 'month']}
                    eventPropGetter={eventStyleGetter}
                    selectable={false}
                    popup={true}
                    onSelectEvent={(event) => {
                        setSelectedEvent(event);
                        setShowEventModal(true);
                    }}
                    components={{
                        event: (props) => {
                            const event = props.event;
                            return(
                            <div 
                                {...props}
                                title={event.tooltip || event.title}
                                style={{
                                    ...props.style,
                                    padding: '4px 8px',
                                    fontSize: '11px',
                                    whiteSpace: 'normal',
                                    overflow: 'visible',
                                    textOverflow: '',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center',
                                    textAlign: 'start',
                                    minHeight: '32px',
                                }}
                            >
                                <div style={{ fontWeight: 'bold'}}>
                                    {event.ot_codigo || 'OT'}
                                </div>
                                <div>
                                    {event.proceso_codigo || ''} - {event.proceso_descripcion || ''}
                                </div>
                                <div>
                                    {event.cantidad_intervalo || 0} / {event.cantidad_total || 0}
                                </div>
                                {event.id === 'item_1058_11' && console.log("Evento renderizado en timeline:", event)}
                            </div>
                        )}
                    }}
                    min={dateRange.start}
                    max={dateRange.end}
                    dayLayoutAlgorithm="no-overlap"
                    /*slotPropGetter={(date) => {
                        const isWeekend = moment(date).day() === 0 || moment(date).day() === 6;
                        const hour = moment(date).hour();
                        const isWorkingHour = hour >= 7 && hour < 19;
                        let className = '';
                        if (isWorkingHour) {
                            className = 'rbc-working-hour';
                        } else if (hour < 7 || hour >= 19) {
                            className = 'rbc-non-working-hour';
                        }
                        return {
                            style: {
                                backgroundColor: isWeekend ? '#f8f9fa' : 
                                               isWorkingHour ? 'white' : '#f5f5f5',
                                borderColor: isWeekend ? '#dee2e6' : '#e9ecef',
                                display: hour < 7 || hour >= 19 ? 'none' : 'block'
                            },
                            className: className
                        };
                    }}*/
                    formats={{
                        dayFormat: 'dddd DD/MM/YYYY',
                        dayRangeHeaderFormat: ({ start, end }) => 
                            `${moment(start).format('DD/MM')} - ${moment(end).format('DD/MM/YYYY')}`,
                        monthHeaderFormat: 'MMMM YYYY',
                        timeGutterFormat: (date) => {
                            const hour = moment(date).hour();
                            if (hour >= 7 && hour < 19) {
                                return moment(date).format('HH:mm');
                            }
                            return '';
                        }
                    }}
                    step={30}
                    timeslots={2}
                    onNavigate={(newDate) => {
                        const minDate = moment(dateRange.start);
                        const maxDate = moment(dateRange.end);
                        const newMoment = moment(newDate);
                        if (newMoment.isBefore(minDate)) {
                            setCurrentDate(minDate.toDate());
                        } else if (newMoment.isAfter(maxDate)) {
                            setCurrentDate(maxDate.toDate());
                        } else {
                            setCurrentDate(newDate);
                        }
                    }}
                    scrollToTime={moment().startOf('day').add(8, 'hours').toDate()}
                    slotPropGetter={(date) => ({
                        className: moment(date).hour() >= 8 && moment(date).hour() < 18
                            ? 'working-hours'
                            : 'non-working-hours'
                    })}
                    onScroll={(e) => {
                        if (e.target.scrollLeft !== 0) {
                            e.target.scrollLeft = 0;
                        }
                    }}
                    onDoubleClickEvent={(event) => {
                        setSelectedEvent(event);
                        setShowEventModal(true);
                    }}
                    onSelectSlot={(slotInfo) => {
                        // Puedes agregar lógica aquí si lo necesitas
                    }}
                />
            </div>
            {/* Modal de detalles */}
            <EventDetailsModal
                show={showEventModal}
                onHide={() => {
                    setShowEventModal(false);
                    setSelectedEvent(null);
                }}
                event={selectedEvent}
            />
        </div>
    );
};