import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
    Button, Card, Alert, Row, Col, Badge, Modal, Table, Collapse 
} from 'react-bootstrap';
import { ReactSortable } from 'react-sortablejs';
import { toast } from 'react-hot-toast';
import { FaArrowLeft, FaHistory, FaExclamationTriangle, FaSave, FaFileCode, FaCalendarCheck, FaChartLine, FaChartBar } from 'react-icons/fa';

// Imports de componentes base
import CompNavbar from '../../../components/Navbar/CompNavbar';
import { Footer } from '../../../components/Footer/Footer';
import { LoadingSpinner } from '../../../components/UI/LoadingSpinner/LoadingSpinner';

// Imports de nuevos componentes modulares
import { OrderCard } from '../../../new_components/Program/Details/OrderList/OrderCard';
import { ProcessRow } from '../../../new_components/Program/Details/OrderList/ProcessRow';
import { OrderControls } from '../../../new_components/Program/Details/OrderList/OrderControls';
import { AddOrderModal } from '../../../new_components/Program/Details/Modals/AddOrderModal';
import { ProgressModal } from '../../../new_components/Program/Details/Modals/ProgressModal';
import { AdjustmentsModal } from '../../../new_components/Program/Details/Modals/AdjustmentsModal';
import { TimelineView } from '../../../new_components/Program/Details/Timeline/TimelineView';
import { TimelineControls } from '../../../new_components/Program/Details/Timeline/TimelineControls';
import StatusBadge from '../../../new_components/Program/shared/StatusBadge';
import ProgressBar from '../../../new_components/Program/shared/ProgressBar';

// Imports de hooks personalizados
import { useProgramState } from './state/programSlice';
import { useTimelineState } from './state/timelineSlice';
import { useOrderManagement } from './hooks/useOrderManagement';
import { useProcessProgress } from './hooks/useProcessProgress';

// Imports de utilidades
import { processCalculations } from './utils/processCalculations';
import { timelineHelpers } from './utils/timelineHelpers';

// Imports de APIs
import { 
    generateProgramPDF, 
    verificarReajustesPrograma, 
    aplicarReajustesPrograma,
    getMaquinas, 
    updatePriorities,
    updateProgram,
    updateProductStandard
} from '../../../api/programs.api';
import { checkAuthStatus } from '../../../api/auth.api';

// Imports de componentes originales que mantenemos
import { ProgramMonitoring } from '../../../components/Programa/ProgramMonitoring';
import { ProgramHistory } from '../../../components/Programa/ProgramHistory';
import { TimelineTimeReal } from '../../../components/Programa/TimelineTimeReal';
import { AnalisisAvancesModal } from '../../../components/Programa/AnalisisAvancesModal';
import InconsistenciasModal from '../../../components/Programa/InconsistenciasModal';

import { FinalizarDiaModal } from '../../../new_components/Program/Details/Modals/FinalizarDiaModal';
import { GenerarJsonBaseModal } from '../../../new_components/Program/Details/Modals/GenerarJsonBaseModal';
import { ComparativaAvancesModal } from '../../../new_components/Program/Details/Modals/ComparativaAvancesModal';
import { verificarPlanificacionLista, guardarCambiosPlanificacion } from '../../../api/planificacion.api';


// Styles
import '../../../pages/programs/ProgramDetail.css';

const AlertMessage = ({ type, icon, message }) => (
    <div className={`alert alert-${type} d-flex align-items-center`} role="alert">
        <div className="alert-icon me-3">{icon}</div>
        <div>{message}</div>
    </div>
);

export default function ProgramDetail() {
    const { programId } = useParams();
    const navigate = useNavigate();

    // Estados del programa usando hooks personalizados
    const {
        programData,
        loading,
        otList,
        metricas,
        loadProgramData,
        updateOT,
        removeOT,
        updateProceso,
        checkInconsistencias,
        checkEstandaresCero,
    } = useProgramState(programId);

    // Estados del timeline usando hook personalizado
    const { 
        timelineGroups, 
        timelineItems, 
        timelineMode, 
        showTimeline, 
        timelineLoading,
        toggleTimeline,
        setTimelineMode,
        validateTimelineDisplay
    } = useTimelineState(programId);
    

    // Gestión de órdenes usando hook personalizado
    const {
        orders,
        availableOrders,
        showAddOrderModal,
        setOrderList,
        addOrders,
        removeOrder,
        updateOrderPriorities,
        toggleAddOrderModal,
        //aplicarEstandaresGuardados
    } = useOrderManagement(programId, loadProgramData);

    // Gestión de progreso usando hook personalizado
    const {
        selectedProcess,
        selectedOT,
        showProgressModal,
        showAdjustmentsModal,
        progressData,
        openProgressModal,
        closeProgressModal,
        openAdjustmentsModal,
        closeAdjustmentsModal,
        updateProgress,
        resetProgress
    } = useProcessProgress(programId, updateProceso);

    // Estados locales adicionales
    const [expandedOTs, setExpandedOTs] = useState({});
    const [maquinas, setMaquinas] = useState([]);
    const [isAdmin, setIsAdmin] = useState(false);
    const [showTimelineTimeReal, setShowTimelineTimeReal] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [showInconsistencias, setShowInconsistencias] = useState(false);
    const [showAnalisisAvances, setShowAnalisisAvances] = useState(false);
    const [selectedOtAnalisis, setSelectedOtAnalisis] = useState(null);
    const [otsConInconsistencias, setOtsConInconsistencias] = useState([]);
    const [savingChanges, setSavingChanges] = useState(false);
    const [pendingChanges, setPendingChanges] = useState({});
    const [showPendingChangesAlert, setShowPendingChangesAlert] = useState(false);

    const [showFinalizarDiaModal, setShowFinalizarDiaModal] = useState(false);
    const [showGenerarJsonModal, setShowGenerarJsonModal] = useState(false);
    const [showComparativaModal, setShowComparativaModal] = useState(false);
    const [planificacionLista, setPlanificacionLista] = useState(false);
    const [verificandoPlanificacion, setVerificandoPlanificacion] = useState(false);
    const [cambiosPendientes, setCambiosPendientes] = useState([]);
    const [ultimaComparativa, setUltimaComparativa] = useState(null);
    const [fechaUltimaFinalizacion, setFechaUltimaFinalizacion] = useState(null);


     // ✅ VERIFICAR PLANIFICACIÓN al cargar y cuando cambien los datos
     useEffect(() => {
        if (programId && otList?.length > 0) {
            verificarEstadoPlanificacion();
        }
    }, [programId, otList, metricas]);

    // ✅ DETECTAR CAMBIOS en la planificación
    useEffect(() => {
        // Detectar si hay cambios pendientes (ejemplo: estándares en 0, máquinas sin asignar)
        const cambiosDetectados = [];
        
        otList?.forEach(ot => {
            ot.procesos?.forEach(proceso => {
                if (!proceso.estandar || proceso.estandar === 0) {
                    cambiosDetectados.push({
                        tipo: 'ESTANDAR',
                        ot: ot.orden_trabajo,
                        proceso: proceso.id,
                        descripcion: `Estándar faltante en ${proceso.descripcion}`
                    });
                }
                if (!proceso.maquina_id) {
                    cambiosDetectados.push({
                        tipo: 'MAQUINA',
                        ot: ot.orden_trabajo,
                        proceso: proceso.id,
                        descripcion: `Máquina sin asignar en ${proceso.descripcion}`
                    });
                }
            });
        });
        
        setCambiosPendientes(cambiosDetectados);
    }, [otList]);

    // ✅ FUNCIÓN para verificar estado de planificación
    const verificarEstadoPlanificacion = async () => {
        try {
            setVerificandoPlanificacion(true);
            const resultado = await verificarPlanificacionLista(programId);
            setPlanificacionLista(resultado.planificacion_lista);
        } catch (error) {
            console.error('Error verificando planificación:', error);
        } finally {
            setVerificandoPlanificacion(false);
        }
    };

    // ✅ FUNCIÓN para guardar cambios pendientes
    const handleGuardarCambios = async () => {
        if (cambiosPendientes.length === 0) {
            toast.info('No hay cambios pendientes para guardar');
            return;
        }

        try {
            await guardarCambiosPlanificacion(programId, cambiosPendientes);
            toast.success('✅ Cambios guardados correctamente');
            setCambiosPendientes([]);
            verificarEstadoPlanificacion(); // Re-verificar después de guardar
        } catch (error) {
            console.error('Error guardando cambios:', error);
            toast.error('❌ Error al guardar cambios');
        }
    };

    // ✅ HANDLERS para los modales
    const handleJsonGenerado = (resultado) => {
        toast.success(`📄 JSON base generado: ${resultado.datosGenerados.total_ots} OTs, ${resultado.datosGenerados.total_procesos} procesos`);
        // La planificación ya tiene JSON base, actualizar estado
        verificarEstadoPlanificacion();
    };

    const handleDiaFinalizado = (resultado) => {
        setUltimaComparativa(resultado.comparativa);
        setFechaUltimaFinalizacion(resultado.fechaFinalizada);
        
        // Mostrar modal de comparativa si hay cambios
        if (resultado.comparativa && resultado.cambiosImportados > 0) {
            setShowComparativaModal(true);
        }
        
        // Recargar datos del programa
        loadProgramData();
        
        toast.success(`📅 Día ${resultado.fechaFinalizada} finalizado. Nueva fecha inicio: ${resultado.nuevaFechaInicio}`);
    };

    // ✅ RENDER de botones de planificación (agregar después de los controles existentes)
    const renderBotonesPlanificacion = () => {
        return (
            <div className="card mb-4">
                <div className="card-header d-flex justify-content-between align-items-center">
                    <h6 className="mb-0">🎯 Gestión de Planificación</h6>
                    {verificandoPlanificacion && <LoadingSpinner message="verificando planificacion" />}
                </div>
                <div className="card-body">
                    <div className="d-flex flex-wrap gap-2 align-items-center">
                        
                        {/* Botón Generar JSON Base */}
                        {planificacionLista ? (
                            <Button 
                                variant="success" 
                                size="sm"
                                onClick={() => setShowGenerarJsonModal(true)}
                            >
                                <FaFileCode className="me-1" />
                                Generar Planificación Base
                            </Button>
                        ) : (
                            <Button 
                                variant="outline-secondary" 
                                size="sm"
                                disabled
                                title="Completar requisitos primero"
                            >
                                <FaFileCode className="me-1" />
                                Planificación Incompleta
                            </Button>
                        )}

                        {/* Botón Guardar Cambios */}
                        {cambiosPendientes.length > 0 && (
                            <Button 
                                variant="warning" 
                                size="sm"
                                onClick={handleGuardarCambios}
                            >
                                <FaSave className="me-1" />
                                Guardar Cambios ({cambiosPendientes.length})
                            </Button>
                        )}

                        {/* Botón Finalizar Día */}
                        <Button 
                            variant="primary" 
                            size="sm"
                            onClick={() => setShowFinalizarDiaModal(true)}
                        >
                            <FaCalendarCheck className="me-1" />
                            Finalizar Día
                        </Button>

                        {/* Botón Ver Última Comparativa */}
                        {ultimaComparativa && (
                            <Button 
                                variant="outline-info" 
                                size="sm"
                                onClick={() => setShowComparativaModal(true)}
                            >
                                <FaChartLine className="me-1" />
                                Ver Última Comparativa
                            </Button>
                        )}
                        <Button 
                            variant="info" 
                            size="sm"
                            onClick={() => navigate(`/programs/${programId}/dashboard`)}
                        >
                            <FaChartBar className="me-1" />
                            Ver Dashboard Completo
                        </Button>
                    </div>

                    {/* Indicadores de estado */}
                    <div className="mt-2">
                        {planificacionLista ? (
                            <Alert variant="success" className="py-2 mb-0">
                                <small>
                                    ✅ Planificación lista para generar JSON base
                                </small>
                            </Alert>
                        ) : (
                            <Alert variant="warning" className="py-2 mb-0">
                                <small>
                                    ⚠️ Completar asignaciones de máquinas y estándares antes de generar JSON base
                                </small>
                            </Alert>
                        )}
                    </div>
                </div>
            </div>
        );
    };


    // Verificar autenticación al cargar
    useEffect(() => {
        const { user } = checkAuthStatus();
        setIsAdmin(user?.is_staff || false);
    }, []);

    // Cargar datos iniciales
    useEffect(() => {
        if (programId) {
            loadProgramData();
            console.log('dssddsdsss'+
                timelineItems.values());
            loadMaquinas();
            cargarOTsConInconsistencias();
        }
        console.log(timelineItems, 'items del timeline')
    }, [programId]);

    // Sincronizar órdenes con otList
    useEffect(() => {
        setOrderList(otList);
    }, [otList]);

    // Cargar máquinas
    const loadMaquinas = async () => {
        try {
            const maquinasData = await getMaquinas(programId);
            setMaquinas(maquinasData);
        } catch (error) {
            console.error('Error al cargar máquinas:', error);
            toast.error('Error al cargar las máquinas');
        }
    };

    // Cargar OTs con inconsistencias
    const cargarOTsConInconsistencias = async () => {
        const inconsistencias = checkInconsistencias();
        const otsConProblemas = [...new Set(
            inconsistencias.map(inc => inc.ot_codigo)
        )];
        setOtsConInconsistencias(otsConProblemas);
    };

    // Manejar cambios en procesos
    const handleProcessChange = (otId, procesoId, field, value) => {
        if(!otList){
            console.error("otLIst no está inicializado.");
            return;
        }
        console.log(`Cambio pendiente en OT: ${otId}, Proceso: ${procesoId}, Campo: ${field}, Valor: ${value}`);

        setOrderList(prevOtList => {
            if (!prevOtList) return []; //si es undefined retornamos el array vacío

            const newList = prevOtList.map(ot => {
                if (ot.orden_trabajo === otId && ot.procesos){
                    return {
                        ...ot,
                        procesos: ot.procesos.map(proceso => {
                            if (proceso.id === procesoId){
                                return{
                                    ...proceso,
                                    [field]: value
                                };
                            }
                            return proceso;
                        })
                    };
                }
                return ot;
            });
            return newList;

        })

        const changeKey = `${otId}-${procesoId}-${field}`;
        setPendingChanges(prev => {
            const newChanges = {
            ...prev,
            [changeKey]: { otId, procesoId, field, value }
        };
        console.log("Cambios pendientes:", newChanges);
        setShowPendingChangesAlert(true);

        return newChanges;
        });
    };

    const handleSaveChanges = async () => {
        try {
            setSavingChanges(true);

            //Actualizar el estándar de producto/pieza para cada proceso
            for (const ot of orders) {
                for (const proceso of ot.procesos){
                    if(proceso.id){
                        await updateProductStandard(programId, proceso.id);
                    }
                }
            }
            
            const updates = orders.map((ot, index) => ({
                orden_trabajo: ot.orden_trabajo,
                priority: index + 1,
                procesos: ot.procesos.map(proceso => ({
                    id: proceso.id,
                    maquina_id: proceso.maquina_id,
                    estandar: proceso.estandar
                }))
            }));
            

            await updateProgram(programId, updates);

            setPendingChanges({});
            setShowPendingChangesAlert(false);
            await loadProgramData();

            if (showTimeline){
                loadTimelineData();
            }
            toast.success("Cambios guardados correctamente");
        } catch (error) {
            console.error('Error guardando cambios:', error);
            toast.error(`Error al guardar los cambios: ${error.message}`)
        } finally {
            setSavingChanges(false);
        }
    }

    // Guardar cambios pendientes
    const saveChanges = async (otId) => {
        try {
            setSavingChanges(true);
            const changesForOT = Object.values(pendingChanges).filter(
                change => change.otId === otId
            );

            for (const change of changesForOT) {
                updateProceso(change.otId, change.procesoId, {
                    [change.field]: change.value
                });
            }

            // Limpiar cambios pendientes para esta OT
            const newPendingChanges = {};
            Object.keys(pendingChanges).forEach(key => {
                if (!key.startsWith(`${otId}-`)) {
                    newPendingChanges[key] = pendingChanges[key];
                }
            });
            setPendingChanges(newPendingChanges);
            console.log("cambios: ", newPendingChanges);

            toast.success('Cambios guardados correctamente');
        } catch (error) {
            console.error('Error guardando cambios:', error);
            toast.error('Error al guardar cambios');
        } finally {
            setSavingChanges(false);
        }
    };

    // Manejar expansión/colapso de OTs
    const toggleOTExpansion = (otId) => {
        setExpandedOTs(prev => ({
            ...prev,
            [otId]: !prev[otId]
        }));
    };

    // Generar PDF
    const handleGeneratePDF = async () => {
        try {
            await generateProgramPDF(programId);
            toast.success('PDF generado correctamente');
        } catch (error) {
            console.error('Error generando PDF:', error);
            toast.error('Error al generar PDF');
        }
    };

    // Verificar ajustes
    const handleCheckAdjustments = async () => {
        try {
            const response = await verificarReajustesPrograma(programId);
            if (response.requiere_ajustes) {
                openAdjustmentsModal(response);
            } else {
                toast.success('No se requieren ajustes');
            }
        } catch (error) {
            console.error('Error verificando ajustes:', error);
            toast.error('Error al verificar ajustes');
        }
    };

    // Calcular resumen del programa
    const calcularResumen = () => {
        const procesosPorPlanificar = otList.reduce((acc, ot) => {
            return acc + (ot.procesos?.filter(p => 
                p.estado_proceso !== 'COMPLETADO' && 
                p.porcentaje_completado < 100
            ).length || 0);
        }, 0);
    
        const inconsistencias = checkInconsistencias();
        const estandaresCero = checkEstandaresCero();
    
        // ✅ VERIFICAR que otList existe y tiene datos
        if (!otList || otList.length === 0) {
            return {
                procesosPorPlanificar: 0,
                inconsistencias: inconsistencias.length,
                estandaresCero: estandaresCero.length,
                // Valores de kilos
                kilosTotalPlanificados: 0,
                kilosTotalFabricados: 0,
                totalKilosFabricados: 0,
                totalKilosPlanificados: 0,
                // Valores de dinero
                valorTotalPrograma: 0,
                valorTotalFabricado: 0,
                ...metricas
            };
        }

        console.log('=== DEBUGGING CALCULAR RESUMEN ===');
        console.log('otList.length:', otList.length);
        console.log('otList data:', otList);
    
        // ✅ CÁLCULOS con validación de datos
        const totales = otList.reduce((acc, ot, index) => {
            // Extraer y validar datos de cada OT
            const cantidadPedido = parseFloat(ot.orden_trabajo_cantidad_pedido || 0);
            const cantidadAvance = parseFloat(ot.orden_trabajo_cantidad_avance || 0);
            const pesoUnitario = parseFloat(ot.orden_trabajo_peso || 0);
            const valorUnitario = parseFloat(ot.orden_trabajo_valor || 0);
            
            // Calcular valores para esta OT (solo si los datos son válidos)
            const valorPlanificado = cantidadPedido * valorUnitario;
            const valorFabricado = cantidadAvance * valorUnitario;
            const kilosPlanificados = cantidadPedido * pesoUnitario;
            const kilosFabricados = cantidadAvance * pesoUnitario;

            console.log(`OT ${index + 1}:`, {
                codigo: ot.orden_trabajo_codigo_ot,
                cantidadPedido,
                cantidadAvance,
                valorUnitario,
                valorPlanificado,
                valorFabricado
            });
            
            // Retornar acumulador actualizado
            return {
                valorTotalPrograma: acc.valorTotalPrograma + valorPlanificado,
                valorTotalFabricado: acc.valorTotalFabricado + valorFabricado,
                kilosTotalPlanificados: acc.kilosTotalPlanificados + kilosPlanificados,
                kilosTotalFabricados: acc.kilosTotalFabricados + kilosFabricados
            };
        }, {
            // Valores iniciales del acumulador
            valorTotalPrograma: 0,
            valorTotalFabricado: 0,
            kilosTotalPlanificados: 0,
            kilosTotalFabricados: 0
        });

        // ✅ LOG RESULTADO FINAL
        console.log('Totales calculados:', totales);
        console.log('Metricas desde useProgramState:', metricas);
    
        // ✅ RETORNAR todos los valores necesarios
        return {
            procesosPorPlanificar,
            inconsistencias: inconsistencias.length,
            estandaresCero: estandaresCero.length,
            
            // Valores de kilos (con nombres consistentes)
            kilosTotalPlanificados: totales.kilosTotalPlanificados || 0,
            kilosTotalFabricados: totales.kilosTotalFabricados || 0,
            totalKilosFabricados: totales.kilosTotalFabricados || 0,    // Para ProgressBar
            totalKilosPlanificados: totales.kilosTotalPlanificados || 0, // Para ProgressBar
            
            // Valores de dinero
            valorTotalPrograma: totales.valorTotalPrograma || 0,
            valorTotalFabricado: totales.valorTotalFabricado || 0,
            
            // Mantener métricas originales
            //...metricas
        };
    };

    // Función para verificar si hay procesos con estándar cero
    const hayProcesosConEstandarCero = () => {
        if (!otList || otList.length === 0) return true;
        
        for (const ot of otList) {
            if (!ot.procesos) continue;
            
            for (const proceso of ot.procesos) {
                const estandar = parseFloat(proceso.estandar);
                if (!estandar || estandar === 0) {
                    console.log('Proceso con estándar cero:', proceso);
                    return true;
                }
            }
        }
        
        return false;
    };

    // Función para manejar el toggle del timeline
    const handleToggleTimeline = () => {
        // Añadir logs de depuración
        console.log('Verificando procesos para timeline:', {
            programId,
            otList: otList?.length || 0,
            procesos: otList?.flatMap(ot => ot.procesos || [])?.length || 0
        });
        
        // Verificar si hay procesos con estándar cero
        if (hayProcesosConEstandarCero()) {
            toast.error(
                <div>
                    <p>No se puede proyectar: Hay procesos con estándar en 0</p>
                    <p>Por favor, corrija los valores antes de proyectar.</p>
                </div>,
                { duration: 5000 }
            );
            return;
        }
        
        // Pasar los procesos al toggleTimeline para validación
        toggleTimeline(otList.flatMap(ot => ot.procesos || []));
    };

    if (loading) {
        return (
            <div className="min-vh-100 d-flex justify-content-center align-items-center">
                <LoadingSpinner message="Cargando programa..." />
            </div>
        );
    }

    if (!programData) {
        return (
            <div className="min-vh-100 d-flex justify-content-center align-items-center">
                <Alert variant="danger">
                    <h5>Error</h5>
                    <p>No se pudieron cargar los datos del programa.</p>
                    <Link to="/programs" className="btn btn-primary">
                        Volver a Programas
                    </Link>
                </Alert>
            </div>
        );
    }

    const resumen = calcularResumen();
    const hasInconsistencies = otsConInconsistencias.length > 0;

    return (
        <div className="min-vh-100 bg-light">
            <CompNavbar />
            
            <div className="container-fluid py-4">
                {/* Header */}
                <Row className="mb-4">
                    <Col>
                        <div className="d-flex justify-content-between align-items-center">
                            <div>
                                <Link 
                                    to="/programs" 
                                    className="btn btn-outline-secondary btn-sm me-3"
                                >
                                    <FaArrowLeft className="me-2" />
                                    Volver
                                </Link>
                                <h2 className="d-inline-block mb-0">
                                    {programData.nombre}
                                </h2>
                                <StatusBadge 
                                    status={programData.estado} 
                                    className="ms-3" 
                                />
                            </div>
                            
                            <div className="d-flex gap-2">
                                <Button 
                                    variant="outline-info" 
                                    onClick={() => setShowHistory(true)}
                                >
                                    <FaHistory className="me-2" />
                                    Historial
                                </Button>
                                
                                {hasInconsistencies && (
                                    <Button 
                                        variant="warning" 
                                        onClick={() => setShowInconsistencias(true)}
                                    >
                                        <FaExclamationTriangle className="me-2" />
                                        Inconsistencias
                                    </Button>
                                )}

                                
                            </div>
                        </div>
                    </Col>
                </Row>

                {/* Resumen del programa */}
                <Row className="mb-4">
                    <Col md={4}>
                        <Card>
                            <Card.Body>
                                <h5>Resumen del Programa</h5>
                                <Row>
                                    <Col md={3}>
                                        <div className="text-center">
                                            <h4 className="text-primary">{resumen.totalProcesos || 0}</h4>
                                            <small className="text-muted">Total Procesos</small>
                                        </div>
                                    </Col>
                                    <Col md={3}>
                                        <div className="text-center">
                                            <h4 className="text-success">{resumen.procesosCompletados || 0}</h4>
                                            <small className="text-muted">Completados</small>
                                        </div>
                                    </Col>
                                    <Col md={3}>
                                        <div className="text-center">
                                            <h4 className="text-warning">{resumen.procesosPorPlanificar || 0}</h4>
                                            <small className="text-muted">Por Planificar</small>
                                        </div>
                                    </Col>
                                    <Col md={3}>
                                        <div className="text-center">
                                            <h4 className="text-info">
                                                {resumen.totalProcesos > 0
                                                    ? `${((resumen.procesosCompletados / resumen.totalProcesos) * 100).toFixed(1)}%`
                                                : '0.0%'}
                                            </h4>
                                            <small className="text-muted">Progreso</small>
                                        </div>
                                    </Col>
                                </Row>
                                
                                {/* Alertas importantes */}
                                {otsConInconsistencias.length > 0 && (
                                    <Alert variant="warning" className="mt-3 mb-0 py-2">
                                        <small>
                                            ⚠️ <strong>{otsConInconsistencias.length} OT(s) con inconsistencias</strong> - 
                                            Resuelva las inconsistencias antes de planificar
                                        </small>
                                    </Alert>
                                )}
                                
                                {resumen.procesosPorPlanificar === 0 && otsConInconsistencias.length === 0 && (
                                    <Alert variant="success" className="mt-3 mb-0 py-2">
                                        <small>🎉 <strong>¡Programa listo!</strong> No hay procesos pendientes ni inconsistencias.</small>
                                    </Alert>
                                )}
                            </Card.Body>
                        </Card>
                    </Col>
                    
                    <Col md={2}>
                        <Card>
                            <Card.Body>
                                <h6>Producción</h6>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Kilos Planificados:</small>
                                        <strong>{resumen.kilosTotalPlanificados.toLocaleString()}</strong>
                                    </div>
                                </div>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Kilos Fabricados:</small>
                                        <strong className="text-success">
                                            {resumen.kilosTotalFabricados.toLocaleString()}
                                        </strong>
                                    </div>
                                </div>
                                <ProgressBar 
                                    current={resumen.kilosTotalFabricados}
                                    total={resumen.kilosTotalPlanificados}
                                    showValues={false}
                                />
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={2}> 
                        <Card>
                            <Card.Body>
                                <h6>Valor</h6>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Valor <br></br>Total Planificado:</small>
                                        <strong>{resumen.valorTotalPrograma.toLocaleString()}</strong>
                                    </div>
                                </div>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Valor Total Fabricado:</small>
                                        <strong className="text-success">
                                            {resumen.valorTotalFabricado.toLocaleString()}
                                        </strong>
                                    </div>
                                </div>
                                <ProgressBar 
                                    current={resumen.valorTotalFabricado}
                                    total={resumen.valorTotalPrograma}
                                    showValues={false}
                                />
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={4}>
                        {renderBotonesPlanificacion()}
                    </Col>
                    
                </Row>

                {/* Controles de timeline */}
                <Row className="mb-4">
                    <Col>
                        <Card>
                            <Card.Body>
                                <div className="d-flex justify-content-between align-items-center">
                                    <h5 className="mb-0">Proyección Temporal</h5>
                                    <TimelineControls
                                        showTimeline={showTimeline}
                                        timelineMode={timelineMode}
                                        timelineLoading={timelineLoading}
                                        onToggleTimeline={handleToggleTimeline}
                                        onModeChange={setTimelineMode}
                                        hasProcessesWithZeroStandard={hayProcesosConEstandarCero()}
                                    />
                                </div>
                                
                                {showTimeline && (
                                    <div className="mt-3">
                                        <TimelineView
                                            timelineGroups={timelineGroups}
                                            timelineItems={timelineItems}
                                            timelineMode={timelineMode}
                                            isLoading={timelineLoading}
                                            key={`timeline-${timelineGroups?.length || 0}-${timelineItems?.length || 0}`} // Forzar re-render cuando cambian los datos
                                        />
                                        
                                    </div>
                                )}
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>

                <Row>
                    {showPendingChangesAlert && Object.keys(pendingChanges).length > 0 && (
                            <div className="alert alert-info" role="alert">
                                <i className="bi bi-info-circle-fill me-2"></i>
                                Hay cambios pendientes por guardar. Por favor, guarde los cambios antes de salir de la página.
                            </div>
                    )}
                </Row>

                {/* Lista de órdenes */}
                <Row>
                    <Col>
                        <Card>
                            <Card.Header>
                                <div className="d-flex justify-content-between align-items-center">
                                    <h5 className="mb-0">Órdenes de Trabajo</h5>
                                    <OrderControls
                                        onAddOrder={toggleAddOrderModal}
                                        onGeneratePDF={handleGeneratePDF}
                                        onShowHistory={() => setShowHistory(true)}
                                        onCheckAdjustments={handleCheckAdjustments}
                                        onShowTimelineReal={() => setShowTimelineTimeReal(true)}
                                        hasInconsistencies={hasInconsistencies}
                                        isAdmin={isAdmin}
                                    />
                                </div>
                            </Card.Header>
                            <Card.Body>
                                <ReactSortable
                                    list={orders}
                                    setList={setOrderList}
                                    onEnd={(evt) => {
                                        const newOtList = [...otList];
                                        const movedItem = newOtList.splice(evt.oldIndex, 1)[0];
                                        newOtList.splice(evt.newIndex, 0, movedItem);
                                        setOrderList(newOtList);
                                        updateOrderPriorities(newOtList);
                                    }}
                                    disabled={savingChanges}
                                    animation={200}
                                    ghostClass="sortable-ghost"
                                    chosenClass="sortable-chosen"
                                    dragClass="sortable-drag"
                                >
                                    {orders.map((ot) => {
                                        const isExpanded = expandedOTs[ot.orden_trabajo];
                                        const tieneAvanceHistorico = ot.tiene_avance_historico;
                                        const tieneInconsistencias = otsConInconsistencias.includes(
                                            ot.orden_trabajo_codigo_ot
                                        );
                                        const maquinasPrincipales = ot.procesos
                                            ?.filter(p => p.es_principal)
                                            .map(p => p.maquina_descripcion) || [];

                                        return (
                                            <OrderCard
                                                key={ot.orden_trabajo}
                                                ot={ot}
                                                isExpanded={isExpanded}
                                                onToggleExpand={() => toggleOTExpansion(ot.orden_trabajo)}
                                                onSaveChanges={() => handleSaveChanges(ot.orden_trabajo)}
                                                savingChanges={savingChanges}
                                                tieneAvanceHistorico={tieneAvanceHistorico}
                                                tieneInconsistencias={tieneInconsistencias}
                                                maquinasPrincipales={maquinasPrincipales}
                                            >
                                                <Collapse in={isExpanded}>
                                                    <div className="table-responsive mt-1" style={{overflowY: 'visible', maxHeight:'none'}}>
                                                        <Table  size="sm">
                                                            <thead>
                                                                <tr>
                                                                    <th>Proceso</th>
                                                                    <th className="text-center">Estándar (u/h)</th>
                                                                    <th className="text">Máquina</th>
                                                                    <th className="text-center">Total</th>
                                                                    <th className="text-center">Completado</th>
                                                                    <th className="text-center">Restante</th>
                                                                    <th className="text-center">Estado</th>
                                                                    <th className="text-center">Acciones</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {ot.procesos?.map((proceso) => {
                                                                    const tieneInconsistenciasProceso = tieneInconsistencias;
                                                                    const incluyeEnPlanificacion = proceso.estado_proceso !== 'COMPLETADO';
                                                                    const tieneAvance = proceso.cantidad_terminado_proceso > 0;

                                                                    return (
                                                                        <ProcessRow
                                                                            key={proceso.id}
                                                                            proceso={proceso}
                                                                            ot={ot}
                                                                            onProcessChange={handleProcessChange}
                                                                            onProcessClick={openProgressModal}
                                                                            onResetProgress={resetProgress}
                                                                            tieneInconsistencias={tieneInconsistenciasProceso}
                                                                            incluyeEnPlanificacion={incluyeEnPlanificacion}
                                                                            tieneAvance={tieneAvance}
                                                                            programId={programId}
                                                                            routesData={timelineItems}
                                                                        />
                                                                    );
                                                                })}
                                                            </tbody>
                                                        </Table>
                                                    </div>
                                                </Collapse>
                                            </OrderCard>
                                        );
                                    })}
                                </ReactSortable>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            </div>

            <Footer />

            {/* Modales */}
            <AddOrderModal
                show={showAddOrderModal}
                onHide={toggleAddOrderModal}
                programId={programId}
                onOrdenesAgregadas={loadProgramData}
            />

            <ProgressModal
                show={showProgressModal}
                onHide={closeProgressModal}
                itemRuta={selectedProcess}
                otData={selectedOT}
                onProgressUpdate={updateProgress}
            />

            <AdjustmentsModal
                show={showAdjustmentsModal}
                onHide={closeAdjustmentsModal}
                adjustments={progressData}
                onApplyAdjustments={(adjustments) => {
                    aplicarReajustesPrograma(programId, adjustments);
                    closeAdjustmentsModal();
                    loadProgramData();
                }}
            />

            {/* ✅ Solo renderizar cuando sea necesario */}
            {showTimelineTimeReal && (
                <TimelineTimeReal
                    programId={programId}
                    show={showTimelineTimeReal}
                    onHide={() => setShowTimelineTimeReal(false)}
                    onTimelineUpdated={loadProgramData}
                />
            )}

            {showHistory && (
                <ProgramHistory 
                    programId={programId} 
                    isAdmin={isAdmin}
                    show={showHistory}
                    onHide={() => setShowHistory(false)}
                />
            )}

            <AnalisisAvancesModal
                show={showAnalisisAvances}
                onHide={() => setShowAnalisisAvances(false)}
                programId={programId}
                otId={selectedOtAnalisis?.orden_trabajo}
                otData={selectedOtAnalisis}
                onAvancesActualizados={() => {
                    loadProgramData();
                    cargarOTsConInconsistencias();
                }}
            />

            <InconsistenciasModal 
                programaId={programId}
                isOpen={showInconsistencias}
                onClose={() => setShowInconsistencias(false)}
            />

            {/* Modal Generar JSON Base */}
            <GenerarJsonBaseModal
                show={showGenerarJsonModal}
                onHide={() => setShowGenerarJsonModal(false)}
                programId={programId}
                programData={programData}
                onJsonGenerado={handleJsonGenerado}
            />

            {/* Modal Finalizar Día */}
            <FinalizarDiaModal
                show={showFinalizarDiaModal}
                onHide={() => setShowFinalizarDiaModal(false)}
                programId={programId}
                programData={programData}
                onDiaFinalizado={handleDiaFinalizado}
            />

            {/* Modal Comparativa */}
            <ComparativaAvancesModal
                show={showComparativaModal}
                onHide={() => setShowComparativaModal(false)}
                comparativa={ultimaComparativa}
                fechaFinalizada={fechaUltimaFinalizacion}
            />

            {/* COMENTAR TEMPORALMENTE PARA TESTING */}
            {/* <ProgramMonitoring programId={programId} /> */}
            {/* <TimelineTimeReal programId={programId} /> */}
        </div>
    );
}
