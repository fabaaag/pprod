import React, { useState, useEffect, useCallback } from 'react';
import { Button, Alert, Badge, Card, Modal, Form, Row, Col, ProgressBar, ButtonGroup } from 'react-bootstrap';
import { toast } from 'react-hot-toast';
import { getTimelineTimeRealWithProgress, finalizarDia } from '../../api/programs.api';
import { ItemRutaProgressModal } from './ItemRutaProgressModal';
import { LoadingSpinner } from '../UI/LoadingSpinner/LoadingSpinner';
import Timeline from "react-calendar-timeline";
import "react-calendar-timeline/dist/Timeline.scss";
import moment from "moment";
import './css/TimelineTimeReal.css';

export function TimelineTimeReal({ programId, onTimelineUpdated }) {
  const [timelineData, setTimelineData] = useState({ groups: [], items: [], ots: [] });
  const [loading, setLoading] = useState(false);
  const [selectedItemRuta, setSelectedItemRuta] = useState(null);
  const [selectedOtData, setSelectedOtData] = useState(null);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [showFinalizarModal, setShowFinalizarModal] = useState(false);
  const [finalizandoDia, setFinalizandoDia] = useState(false);
  const [fechaFinalizacion, setFechaFinalizacion] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [lastUpdate, setLastUpdate] = useState(null);
  const [viewMode, setViewMode] = useState('timeline'); // 'timeline' o 'cards'
  
  // NUEVO: Estados para control de escalas de tiempo
  const [timeScale, setTimeScale] = useState('day'); // 'hour', 'day', 'week', 'month', 'year'
  const [visibleTimeStart, setVisibleTimeStart] = useState(moment().startOf('day').valueOf());
  const [visibleTimeEnd, setVisibleTimeEnd] = useState(moment().add(7, 'days').endOf('day').valueOf());

  // NUEVO: Configuración de horario laboral
  const HORARIO_TRABAJO = {
    inicio: { hora: 7, minuto: 45 }, // 7:45 AM
    fin: { hora: 17, minuto: 45 }    // 5:45 PM
  };

  // NUEVO: Configuraciones de tiempo por escala
  const getTimeConfiguration = (scale) => {
    const now = moment();
    
    switch (scale) {
      case 'hour':
        return {
          defaultTimeStart: now.startOf('day').hour(6).valueOf(), // Empezar una hora antes
          defaultTimeEnd: now.add(1, 'days').endOf('day').hour(19).valueOf(), // Terminar una hora después
          timeSteps: {
            second: 1,
            minute: 1,
            hour: 1,
            day: 1,
            month: 1,
            year: 1
          },
          minZoom: 15 * 60 * 1000, // 15 minutos para ver detalles
          maxZoom: 7 * 24 * 60 * 60 * 1000 // 7 días
        };
      
      case 'day':
        return {
          defaultTimeStart: now.startOf('day').hour(6).valueOf(),
          defaultTimeEnd: now.add(7, 'days').endOf('day').hour(19).valueOf(),
          timeSteps: {
            second: 1,
            minute: 1,
            hour: 1,
            day: 1,
            month: 1,
            year: 1
          },
          minZoom: 2 * 60 * 60 * 1000, // 2 horas mínimo
          maxZoom: 3 * 30 * 24 * 60 * 60 * 1000 // 3 meses
        };
      
      case 'week':
        return {
          defaultTimeStart: now.startOf('month').valueOf(),
          defaultTimeEnd: now.add(6, 'months').endOf('month').valueOf(),
          timeSteps: {
            second: 1,
            minute: 1,
            hour: 1,
            day: 1,
            month: 1,
            year: 1
          },
          minZoom: 7 * 24 * 60 * 60 * 1000, // 1 semana
          maxZoom: 12 * 30 * 24 * 60 * 60 * 1000 // 1 año
        };
      
      case 'month':
        return {
          defaultTimeStart: now.startOf('year').valueOf(),
          defaultTimeEnd: now.add(2, 'years').endOf('year').valueOf(),
          timeSteps: {
            second: 1,
            minute: 1,
            hour: 1,
            day: 1,
            month: 1,
            year: 1
          },
          minZoom: 30 * 24 * 60 * 60 * 1000, // 1 mes
          maxZoom: 5 * 365 * 24 * 60 * 60 * 1000 // 5 años
        };
      
      case 'year':
        return {
          defaultTimeStart: now.subtract(2, 'years').startOf('year').valueOf(),
          defaultTimeEnd: now.add(5, 'years').endOf('year').valueOf(),
          timeSteps: {
            second: 1,
            minute: 1,
            hour: 1,
            day: 1,
            month: 1,
            year: 1
          },
          minZoom: 365 * 24 * 60 * 60 * 1000, // 1 año
          maxZoom: 10 * 365 * 24 * 60 * 60 * 1000 // 10 años
        };
      
      default:
        return getTimeConfiguration('day');
    }
  };

  // NUEVO: Manejar cambio de escala de tiempo
  const handleTimeScaleChange = (newScale) => {
    setTimeScale(newScale);
    const config = getTimeConfiguration(newScale);
    setVisibleTimeStart(config.defaultTimeStart);
    setVisibleTimeEnd(config.defaultTimeEnd);
  };

  // NUEVO: Navegación rápida por fechas
  const handleQuickNavigation = (action) => {
    const duration = visibleTimeEnd - visibleTimeStart;
    
    switch (action) {
      case 'today':
        const today = moment().startOf('day').valueOf();
        setVisibleTimeStart(today);
        setVisibleTimeEnd(today + duration);
        break;
      
      case 'prev':
        setVisibleTimeStart(prev => prev - duration);
        setVisibleTimeEnd(prev => prev - duration);
        break;
      
      case 'next':
        setVisibleTimeStart(prev => prev + duration);
        setVisibleTimeEnd(prev => prev + duration);
        break;
      
      case 'fit':
        // Ajustar al rango de datos si hay items
        if (timelineData.items && timelineData.items.length > 0) {
          const itemTimes = timelineData.items.map(item => [item.start_time, item.end_time]).flat();
          const minTime = Math.min(...itemTimes);
          const maxTime = Math.max(...itemTimes);
          const padding = (maxTime - minTime) * 0.1; // 10% de padding
          
          setVisibleTimeStart(minTime - padding);
          setVisibleTimeEnd(maxTime + padding);
        }
        break;
    }
  };

  // MEJORADO: Función para extender items al horario laboral completo
  const convertTimelineData = (timelineData) => {
    if (!timelineData || !timelineData.items) return timelineData;
    
    // Convertir items para react-calendar-timeline con extensión al horario laboral
    const convertedItems = timelineData.items.map(item => {
      // Obtener fecha base del item (sin hora)
      const fechaBase = moment(item.start_time);
      
      // Crear horarios de inicio y fin de jornada laboral
      const inicioJornada = moment(fechaBase)
        .hour(HORARIO_TRABAJO.inicio.hora)
        .minute(HORARIO_TRABAJO.inicio.minuto)
        .second(0)
        .millisecond(0);
      
      const finJornada = moment(fechaBase)
        .hour(HORARIO_TRABAJO.fin.hora)
        .minute(HORARIO_TRABAJO.fin.minuto)
        .second(0)
        .millisecond(0);

      // Si el proceso se extiende a múltiples días, manejar cada día por separado
      const fechaOriginalFin = moment(item.end_time);
      let fechaFinAjustada = finJornada;

      // Si el proceso termina en un día diferente, extender al final de esa jornada
      if (!fechaOriginalFin.isSame(fechaBase, 'day')) {
        fechaFinAjustada = moment(fechaOriginalFin)
          .hour(HORARIO_TRABAJO.fin.hora)
          .minute(HORARIO_TRABAJO.fin.minuto)
          .second(0)
          .millisecond(0);
      }

      return {
        ...item,
        start_time: moment(item.start_time).toDate(),
        end_time: moment(item.end_time).toDate(),
        // Agregar información original para referencia
        originalStartTime: moment(item.start_time).valueOf(),
        originalEndTime: moment(item.end_time).valueOf(),
        // Mejorar el título para mostrar información de horario real
        title: `${item.title} `, //| ${moment(item.start_time).format('HH:mm')}-${moment(item.end_time).format('HH:mm')}
        itemProps: {
          ...item.itemProps,
          // Agregar datos adicionales
          'data-horario-real-inicio': moment(item.start_time).format('HH:mm'),
          'data-horario-real-fin': moment(item.end_time).format('HH:mm'),
          'data-extended-view': true,
          style: {
            ...item.itemProps?.style,
            // Agregar patrón visual para indicar que es vista extendida
            background: `linear-gradient(90deg, 
              transparent 0%, 
              ${item.itemProps?.style?.backgroundColor || '#007bff'} 20%, 
              ${item.itemProps?.style?.backgroundColor || '#007bff'} 80%, 
              transparent 100%
            )`,
            border: `2px solid ${item.itemProps?.style?.backgroundColor || '#007bff'}`,
            borderRadius: '4px',
            opacity: 0.8
          }
        }
      };
    });
    
    return {
      ...timelineData,
      items: convertedItems
    };
  };

  // NUEVO: Función para crear items de múltiples días
  const expandMultiDayItems = (items) => {
    const expandedItems = [];
    
    items.forEach(item => {
      const startDate = moment(item.originalStartTime || item.start_time);
      const endDate = moment(item.originalEndTime || item.end_time);
      
      // Si el proceso se extiende por múltiples días
      if (!startDate.isSame(endDate, 'day')) {
        let currentDate = moment(startDate).startOf('day');
        let dayCounter = 1;
        
        while (currentDate.isSameOrBefore(endDate, 'day')) {
          const inicioJornada = moment(currentDate)
            .hour(HORARIO_TRABAJO.inicio.hora)
            .minute(HORARIO_TRABAJO.inicio.minuto);
          
          const finJornada = moment(currentDate)
            .hour(HORARIO_TRABAJO.fin.hora)
            .minute(HORARIO_TRABAJO.fin.minuto);
          
          // Para el primer día, usar horario real de inicio si es después de 7:45
          let inicioReal = inicioJornada;
          if (currentDate.isSame(startDate, 'day') && startDate.isAfter(inicioJornada)) {
            inicioReal = startDate;
          }
          
          // Para el último día, usar horario real de fin si es antes de 17:45
          let finReal = finJornada;
          if (currentDate.isSame(endDate, 'day') && endDate.isBefore(finJornada)) {
            finReal = endDate;
          }
          
          expandedItems.push({
            ...item,
            id: `${item.id}_day_${dayCounter}`,
            start_time: inicioJornada.valueOf(),
            end_time: finJornada.valueOf(),
            originalStartTime: inicioReal.valueOf(),
            originalEndTime: finReal.valueOf(),
            title: `${item.title} (Día ${dayCounter}) | ${inicioReal.format('HH:mm')}-${finReal.format('HH:mm')}`,
            itemProps: {
              ...item.itemProps,
              'data-horario-real-inicio': inicioReal.format('HH:mm'),
              'data-horario-real-fin': finReal.format('HH:mm'),
              'data-day-number': dayCounter,
              'data-is-multi-day': true,
              style: {
                ...item.itemProps?.style,
                background: `linear-gradient(90deg, 
                  transparent 0%, 
                  ${item.itemProps?.style?.backgroundColor || '#007bff'} 10%, 
                  ${item.itemProps?.style?.backgroundColor || '#007bff'} 90%, 
                  transparent 100%
                )`,
                border: `2px solid ${item.itemProps?.style?.backgroundColor || '#007bff'}`,
                borderRadius: '4px',
                opacity: 0.8
              }
            }
          });
          
          currentDate.add(1, 'day');
          dayCounter++;
        }
      } else {
        // Item de un solo día, usar la función original
        expandedItems.push(item);
      }
    });
    
    return expandedItems;
  };

  // MEJORADO: Cargar datos con extensión de horario
  const loadTimelineData = useCallback(async () => {
    if (!programId) return;

    try {
      setLoading(true);
      console.log(`[🔍 DEBUG] === CARGANDO TIMELINE PROGRAMA ${programId} ===`);
      
      const response = await getTimelineTimeRealWithProgress(programId);
      
      console.log('[📥 RESPUESTA COMPLETA]:', response);
      console.log('[📊 DATOS RECIBIDOS]:', {
        tipo: response.tipo,
        totalGroups: response.groups?.length || 0,
        totalItems: response.items?.length || 0,  
        totalOTs: response.ots?.length || 0,
        metadata: response.metadata
      });
      
      if (response.items && response.items.length > 0) {
        console.log('[📦 PRIMER ITEM (antes conversión)]:', response.items[0]);
      }
      
      // Validar estructura de datos
      if (!response || typeof response !== 'object') {
        throw new Error('Respuesta inválida del servidor');
      }

      // NUEVO: Convertir fechas y extender al horario laboral
      let timelineDataConverted = convertTimelineData(response);
      
      // NUEVO: Expandir items de múltiples días
      if (timelineDataConverted.items && timelineDataConverted.items.length > 0) {
        timelineDataConverted.items = expandMultiDayItems(timelineDataConverted.items);
        console.log('[📦 ITEMS DESPUÉS DE EXPANSIÓN]:', timelineDataConverted.items.length);
      }

      // Asegurar estructura básica
      const timelineDataFixed = {
        groups: timelineDataConverted.groups || [],
        items: timelineDataConverted.items || [],
        ots: timelineDataConverted.ots || [],
        metadata: timelineDataConverted.metadata || {}
      };

      setTimelineData(timelineDataFixed);
      setLastUpdate(new Date());
      
      if (onTimelineUpdated) {
        onTimelineUpdated(timelineDataFixed);
      }

      console.log(`[✅ TIMELINE PROCESADA]: ${timelineDataFixed.groups.length} grupos, ${timelineDataFixed.items.length} items`);
      
    } catch (error) {
      console.error('[❌ ERROR] cargando timeline tiempo real:', error);
      toast.error('Error al cargar datos en tiempo real');
      
      // Establecer datos vacíos en caso de error
      setTimelineData({ groups: [], items: [], ots: [] });
    } finally {
      setLoading(false);
    }
  }, [programId, onTimelineUpdated]);

  // Cargar datos al montar componente
  useEffect(() => {
    loadTimelineData();
  }, [loadTimelineData]);

  // Manejar click en item de timeline
  const handleItemClick = (itemId, e, time) => {
    console.log('[Frontend] Click en item timeline:', itemId);
    
    const item = timelineData.items?.find(i => i.id === itemId);
    if (!item?.itemProps['data-clickeable']) {
      toast.info('Este proceso no permite edición directa');
      return;
    }

    const itemRutaId = item.itemProps['data-item-ruta-id'];
    const otCodigo = item.itemProps['data-ot-codigo'];
    
    console.log(`[Frontend] Buscando datos para ItemRuta ${itemRutaId}, OT ${otCodigo}`);
    
    // Buscar datos completos en la estructura de OTs
    let itemRutaCompleto = null;
    let otCompleta = null;
    
    timelineData.ots?.forEach(ot => {
      const proceso = ot.procesos.find(p => p.item_ruta_id === itemRutaId);
      if (proceso) {
        itemRutaCompleto = proceso;
        otCompleta = ot;
      }
    });

    if (itemRutaCompleto && otCompleta) {
      console.log('[Frontend] Datos encontrados, abriendo modal');
      setSelectedItemRuta(itemRutaCompleto);
      setSelectedOtData(otCompleta);
      setShowProgressModal(true);
    } else {
      console.error('[Frontend] No se encontraron los datos del proceso');
      toast.error('No se encontraron los datos del proceso');
    }
  };

  // Manejar click en card de proceso
  const handleProcesoCardClick = (proceso, ot) => {
    if (!proceso.clickeable) {
      toast.info('Este proceso no permite edición directa');
      return;
    }

    setSelectedItemRuta(proceso);
    setSelectedOtData(ot);
    setShowProgressModal(true);
  };

  // Manejar actualización de progreso
  const handleProgressUpdated = async (updatedData) => {
    console.log('[Frontend] Actualizando progreso:', updatedData);
    
    // Actualizar datos locales
    setTimelineData(prevData => {
      const newData = { ...prevData };
      
      // Actualizar en estructura de OTs
      newData.ots = newData.ots.map(ot => ({
        ...ot,
        procesos: ot.procesos.map(proceso => {
          if (proceso.item_ruta_id === updatedData.id) {
            return {
              ...proceso,
              cantidad_completada: updatedData.cantidad_terminado_proceso,
              cantidad_pendiente: updatedData.cantidad_pendiente,
              porcentaje_completado: updatedData.porcentaje_completado || 0,
              estado_proceso: updatedData.estado_proceso,
              fecha_inicio_real: updatedData.fecha_inicio_real,
              fecha_fin_real: updatedData.fecha_fin_real,
              operador_actual: updatedData.operador_actual,
              observaciones: updatedData.observaciones_progreso,
              ultima_actualizacion: updatedData.ultima_actualizacion
            };
          }
          return proceso;
        })
      }));
      
      // Actualizar items de timeline
      newData.items = newData.items.map(item => {
        if (item.itemProps && item.itemProps['data-item-ruta-id'] === updatedData.id) {
          const nuevoPorcentaje = updatedData.porcentaje_completado || 0;
          return {
            ...item,
            title: `${updatedData.estado_proceso} - ${nuevoPorcentaje.toFixed(1)}%`,
            itemProps: {
              ...item.itemProps,
              'data-porcentaje': nuevoPorcentaje,
              'data-estado': updatedData.estado_proceso,
              style: {
                ...item.itemProps.style,
                backgroundColor: getColorForEstado(updatedData.estado_proceso, nuevoPorcentaje)
              }
            }
          };
        }
        return item;
      });

      return newData;
    });

    if (onTimelineUpdated) {
      onTimelineUpdated(updatedData);
    }

    toast.success('Progreso actualizado exitosamente');
    setShowProgressModal(false);
  };

  // Obtener color basado en estado y progreso
  const getColorForEstado = (estado, porcentaje) => {
    if (estado === 'COMPLETADO' || porcentaje >= 100) {
      return '#28a745'; // Verde
    } else if (estado === 'EN_PROCESO') {
      if (porcentaje >= 75) return '#007bff'; // Azul
      if (porcentaje >= 50) return '#ffc107'; // Amarillo  
      return '#fd7e14'; // Naranja
    } else if (estado === 'PAUSADO') {
      return '#dc3545'; // Rojo
    }
    return '#6c757d'; // Gris
  };

  // Manejar finalizar día
  const handleFinalizarDia = async () => {
    try {
      setFinalizandoDia(true);
      const resultado = await finalizarDia(programId, fechaFinalizacion);
      
      if (resultado.success) {
        toast.success(resultado.mensaje);
        await loadTimelineData();
        
        if (onTimelineUpdated) {
          onTimelineUpdated({ tipo: 'DIA_FINALIZADO', data: resultado });
        }
      } else {
        toast.error(resultado.mensaje || 'Error finalizando día');
      }
    } catch (error) {
      console.error('Error finalizando día:', error);
      toast.error('Error finalizando día');
    } finally {
      setFinalizandoDia(false);
      setShowFinalizarModal(false);
    }
  };

  // Renderizar vista de cards como alternativa
  const renderCardsView = () => (
    <div className="timeline-cards-view">
      {timelineData.ots?.map(ot => (
        <Card key={ot.id} className="mb-3 ot-timeline-card">
          <Card.Header className="d-flex justify-content-between align-items-center">
            <div>
              <h6 className="mb-0">📋 OT {ot.orden_trabajo_codigo_ot}</h6>
              <small className="text-muted">{ot.descripcion}</small>
            </div>
            <Badge bg={ot.porcentaje_avance_ot >= 100 ? 'success' : ot.porcentaje_avance_ot >= 50 ? 'primary' : 'secondary'}>
              {ot.porcentaje_avance_ot.toFixed(1)}%
            </Badge>
          </Card.Header>
          <Card.Body>
            <Row>
              {ot.procesos?.map(proceso => (
                <Col md={6} lg={4} key={proceso.item_ruta_id} className="mb-3">
                  <Card 
                    className={`proceso-card h-100 ${proceso.clickeable ? 'clickeable' : ''}`}
                    onClick={() => handleProcesoCardClick(proceso, ot)}
                    style={{ cursor: proceso.clickeable ? 'pointer' : 'default' }}
                  >
                    <Card.Body className="p-3">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="mb-0">{proceso.item}. {proceso.proceso.descripcion}</h6>
                        <Badge bg={getEstadoBadgeColor(proceso.estado_proceso)}>
                          {proceso.estado_proceso}
                        </Badge>
                      </div>
                      
                      <div className="mb-2">
                        <small className="text-muted">
                          🏭 {proceso.maquina.descripcion}
                        </small>
                      </div>
                      
                      <ProgressBar 
                        now={proceso.porcentaje_completado} 
                        variant={getProgressVariant(proceso.porcentaje_completado)}
                        className="mb-2"
                        style={{ height: '8px' }}
                      />
                      
                      <div className="d-flex justify-content-between">
                        <small>{proceso.cantidad_completada}/{proceso.cantidad_total}</small>
                        <small>{proceso.porcentaje_completado.toFixed(1)}%</small>
                      </div>
                      
                      {proceso.operador_actual && (
                        <div className="mt-2">
                          <small className="text-info">
                            👤 {proceso.operador_actual.nombre}
                          </small>
                        </div>
                      )}
                      
                      {proceso.clickeable && (
                        <div className="mt-2">
                          <small className="text-primary">
                            📊 Click para actualizar progreso
                          </small>
                        </div>
                      )}
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card.Body>
        </Card>
      ))}
    </div>
  );

  const getEstadoBadgeColor = (estado) => {
    switch (estado) {
      case 'COMPLETADO': return 'success';
      case 'EN_PROCESO': return 'primary';
      case 'PAUSADO': return 'warning';
      case 'PENDIENTE': return 'secondary';
      default: return 'light';
    }
  };

  const getProgressVariant = (porcentaje) => {
    if (porcentaje >= 100) return 'success';
    if (porcentaje >= 75) return 'info';
    if (porcentaje >= 50) return 'warning';
    return 'danger';
  };

  // Debuging de datos
  console.log('[Frontend] Estado actual timeline:', {
    loading,
    groups: timelineData?.groups?.length || 0,
    items: timelineData?.items?.length || 0,
    ots: timelineData?.ots?.length || 0
  });

  if (loading && (!timelineData?.groups?.length && !timelineData?.ots?.length)) {
    return (
      <Card className="text-center">
        <Card.Body>
          <LoadingSpinner />
          <p className="mt-2">Cargando timeline tiempo real...</p>
        </Card.Body>
      </Card>
    );
  }

  return (
    <div className="timeline-tiempo-real-container">
      {/* Header con controles mejorados */}
      <Card className="mb-3">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-0">Timeline Tiempo Real</h5>
            <small className="text-muted">
              Horario laboral: {HORARIO_TRABAJO.inicio.hora}:{HORARIO_TRABAJO.inicio.minuto.toString().padStart(2, '0')} - {HORARIO_TRABAJO.fin.hora}:{HORARIO_TRABAJO.fin.minuto.toString().padStart(2, '0')}
            </small>
            {lastUpdate && (
              <small className="text-muted ms-3">
              Última actualización: {lastUpdate.toLocaleTimeString()}
            </small>
          )}
        </div>
          <div className="d-flex gap-2 align-items-center">
            <Badge bg="info">
              Progreso General: {timelineData.metadata?.progreso_general?.toFixed(1) || 0}%
            </Badge>
            
            {/* NUEVO: Controles de escala de tiempo */}
            <ButtonGroup size="sm">
              {['hour', 'day', 'week', 'month', 'year'].map(scale => (
                <Button
                  key={scale}
                  variant={timeScale === scale ? 'primary' : 'outline-primary'}
                  onClick={() => handleTimeScaleChange(scale)}
                  title={`Vista por ${scale === 'hour' ? 'horas' : scale === 'day' ? 'días' : scale === 'week' ? 'semanas' : scale === 'month' ? 'meses' : 'años'}`}
                >
                  {scale === 'hour' ? 'H' : scale === 'day' ? 'D' : scale === 'week' ? 'S' : scale === 'month' ? 'M' : 'A'}
                </Button>
              ))}
            </ButtonGroup>

            {/* NUEVO: Navegación rápida */}
            <ButtonGroup size="sm">
              <Button
                variant="outline-secondary"
                onClick={() => handleQuickNavigation('prev')}
                title="Anterior"
              >
                ◀
              </Button>
              <Button
                variant="outline-secondary"
                onClick={() => handleQuickNavigation('today')}
                title="Hoy"
              >
                📅
              </Button>
              <Button
                variant="outline-secondary"
                onClick={() => handleQuickNavigation('next')}
                title="Siguiente"
              >
                ▶
              </Button>
              <Button
                variant="outline-secondary"
                onClick={() => handleQuickNavigation('fit')}
                title="Ajustar a datos"
              >
                🔍
              </Button>
            </ButtonGroup>
            
            {/* Toggle vista */}
            <div className="btn-group" role="group">
              <Button 
                variant={viewMode === 'timeline' ? 'primary' : 'outline-primary'}
                size="sm"
                onClick={() => setViewMode('timeline')}
                disabled={!timelineData?.groups?.length}
              >
                📊 Timeline
              </Button>
          <Button
                variant={viewMode === 'cards' ? 'primary' : 'outline-primary'}
            size="sm"
                onClick={() => setViewMode('cards')}
                disabled={!timelineData?.ots?.length}
          >
                🗂️ Cards
          </Button>
            </div>
          
          <Button
              variant="success" 
              size="sm"
              onClick={() => setShowFinalizarModal(true)}
              disabled={finalizandoDia}
            >
              {finalizandoDia ? 'Finalizando...' : 'Finalizar Día'}
            </Button>
            <Button 
              variant="outline-primary" 
            size="sm"
            onClick={loadTimelineData}
            disabled={loading}
          >
              {loading ? <LoadingSpinner size="sm" /> : '🔄 Actualizar'}
          </Button>
        </div>
      </Card.Header>
      </Card>

      {/* Contenido principal */}
      <div className="timeline-content">
        {console.log('🚨 DEBUG TIMELINE TIEMPO REAL:', {
          groups: timelineData.groups,
          items: timelineData.items,
          groupsLength: timelineData.groups?.length,
          itemsLength: timelineData.items?.length,
          primerGrupo: timelineData.groups?.[0],
          primerItem: timelineData.items?.[0]
        })}
        
        {loading ? (
          <div className="text-center">
            <LoadingSpinner />
            <p className="mt-2">Cargando timeline...</p>
          </div>
        ) : !timelineData?.groups?.length && !timelineData?.ots?.length ? (
          <Alert variant="warning">
            <div className="text-center">
              <h6>No hay procesos para mostrar</h6>
              <p className="mb-0">Aún no hay procesos configurados en este programa.</p>
              <Button 
                variant="outline-primary" 
                size="sm" 
                className="mt-2"
                onClick={loadTimelineData}
              >
                🔄 Reintentar
              </Button>
            </div>
          </Alert>
        ) : viewMode === 'timeline' ? (
          // SIMPLIFICADO: Si hay datos y modo es timeline, mostrar timeline
          <div className="timeline-wrapper">
            <Timeline
              groups={timelineData.groups}
              items={timelineData.items}
              visibleTimeStart={visibleTimeStart}
              visibleTimeEnd={visibleTimeEnd}
              onTimeChange={(visibleTimeStart, visibleTimeEnd) => {
                setVisibleTimeStart(visibleTimeStart);
                setVisibleTimeEnd(visibleTimeEnd);
              }}
              {...getTimeConfiguration(timeScale)}
              onItemClick={handleItemClick}
              itemTouchSendsClick={true}
              stackItems={true}
              itemHeightRatio={0.75}
              canMove={false}
              canResize={false}
              lineHeight={50}
              sidebarWidth={250}
              canZoom={true}
              canChangeGroup={false}
              timeFormat={
                timeScale === 'hour' ? 'HH:mm' :
                timeScale === 'day' ? 'DD/MM' :
                timeScale === 'week' ? 'DD/MM' :
                timeScale === 'month' ? 'MMM YYYY' : 'YYYY'
              }
              itemRenderer={({ item, itemContext, getItemProps }) => (
                <div
                  {...getItemProps({
                    style: {
                      ...item.itemProps?.style,
                      cursor: item.itemProps?.['data-clickeable'] ? 'pointer' : 'default',
                      opacity: item.itemProps?.['data-clickeable'] ? 1 : 0.7,
                      minHeight: '20px',
                      borderRadius: '4px'
                    }
                  })}
                  title={`${item.itemProps?.['data-proceso-descripcion'] || item.title} - ${item.itemProps?.['data-estado'] || 'N/A'} (${item.itemProps?.['data-porcentaje'] || 0}%)`}
                >
                  <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
                    {item.title}
                  </div>
                </div>
              )}
            />
          </div>
        ) : (
          renderCardsView()
        )}
      </div>

      {/* Modales */}
      {showProgressModal && selectedItemRuta && selectedOtData && (
        <ItemRutaProgressModal
          show={showProgressModal}
          onHide={() => setShowProgressModal(false)}
          itemRuta={selectedItemRuta}
          otData={selectedOtData}
          onProgressUpdated={handleProgressUpdated}
        />
      )}

      <Modal show={showFinalizarModal} onHide={() => setShowFinalizarModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Finalizar Día de Producción</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Alert variant="info">
            <strong>¿Qué sucederá?</strong>
            <ul className="mb-0 mt-2">
              <li>Se guardará el progreso actual</li>
              <li>Se regenerará la planificación para mañana</li>
              <li>Se actualizarán las fechas del programa</li>
            </ul>
          </Alert>
          
          <Form.Group>
            <Form.Label>Fecha a Finalizar</Form.Label>
            <Form.Control
              type="date"
              value={fechaFinalizacion}
              onChange={(e) => setFechaFinalizacion(e.target.value)}
              disabled={finalizandoDia}
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowFinalizarModal(false)} disabled={finalizandoDia}>
            Cancelar
          </Button>
          <Button variant="success" onClick={handleFinalizarDia} disabled={finalizandoDia || !fechaFinalizacion}>
            {finalizandoDia ? 'Finalizando...' : 'Finalizar Día'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}