import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
    Button, Card, Alert, Row, Col, Badge, Modal, Table, Collapse 
} from 'react-bootstrap';
import { ReactSortable } from 'react-sortablejs';
import { toast } from 'react-hot-toast';
import { FaArrowLeft, FaHistory, FaExclamationTriangle, FaSave } from 'react-icons/fa';

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

        return {
            procesosPorPlanificar,
            inconsistencias: inconsistencias.length,
            estandaresCero: estandaresCero.length,
            ...metricas
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
                    <Col md={6}>
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
                    
                    <Col md={3}>
                        <Card>
                            <Card.Body>
                                <h6>Producción</h6>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Kilos Planificados:</small>
                                        <strong>{resumen.totalKilosPlanificados.toLocaleString()}</strong>
                                    </div>
                                </div>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>Kilos Fabricados:</small>
                                        <strong className="text-success">
                                            {resumen.totalKilosFabricados.toLocaleString()}
                                        </strong>
                                    </div>
                                </div>
                                <ProgressBar 
                                    current={resumen.totalKilosFabricados}
                                    total={resumen.totalKilosPlanificados}
                                    showValues={false}
                                />
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={3}>
                        <Card>
                            <Card.Body>
                                <h6>Valor</h6>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>$$ Planificados:</small>
                                        <strong>{resumen.valorTotalPrograma.toLocaleString()}</strong>
                                    </div>
                                </div>
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between">
                                        <small>$$ Fabricados:</small>
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

            {/* COMENTAR TEMPORALMENTE PARA TESTING */}
            {/* <ProgramMonitoring programId={programId} /> */}
            {/* <TimelineTimeReal programId={programId} /> */}
        </div>
    );
}
