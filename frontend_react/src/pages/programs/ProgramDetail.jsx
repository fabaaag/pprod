import React, { useEffect, useState } from "react";
import { useParams, Link, redirect, useNavigate } from "react-router-dom";
import { Button, Dropdown, Form, Badge, Card, Collapse, Table, Modal, Alert, ProgressBar, Row, Col } from "react-bootstrap";
import { ReactSortable } from "react-sortablejs";
import CompNavbar from "../../components/Navbar/CompNavbar";
import { Footer } from "../../components/Footer/Footer";
import { getProgram, updatePriorities, deleteOrder, getMaquinas, generateProgramPDF, getProcesoTimeline, verificarReajustesPrograma, aplicarReajustesPrograma, getProgramTimelinePlanning, updateProductStandard, updateItemRutaEstado } from "../../api/programs.api";
import Timeline from "react-calendar-timeline";
import "react-calendar-timeline/dist/Timeline.scss";
import { toast } from "react-hot-toast";
import moment from "moment";
import { LoadingSpinner } from "../../components/UI/LoadingSpinner/LoadingSpinner";
import "./ProgramDetail.css";
import { FaArrowLeft, FaCalendarAlt, FaFlag, FaFilePdf, FaClipboardList, FaExclamationTriangle, FaSave, FaChevronDown, FaPlus, FaHistory, FaEdit } from "react-icons/fa";
import { ProgramMonitoring } from "../../components/Programa/ProgramMonitoring";
import { AgregarOrdenModal } from '../../components/Programa/AgregarOrdenModal';
//import { supervisorReportAPI } from "../../api/supervisorReport.api";
import { ProgramHistory } from "../../components/Programa/ProgramHistory";
import { checkAuthStatus } from '../../api/auth.api';
import { TimelineTimeReal } from '../../components/Programa/TimelineTimeReal';
import { ItemRutaProgressModal } from '../../components/Programa/ItemRutaProgressModal';
import { updateItemRutaProgress, previewReagendarPrograma, aplicarReagendarPrograma } from '../../api/programs.api';
import { AnalisisAvancesModal } from '../../components/Programa/AnalisisAvancesModal';
import axios from '../../api/axiosConfig';
import InconsistenciasModal from '../../components/Programa/InconsistenciasModal';


const AlertMessage = ({ type, icon, message }) => (
    <div className={`alert alert-${type} d-flex align-items-center`} role="alert">
        <div className="alert-icon me-3">
            {icon}
        </div>
        <div>{message}</div>
    </div>
);

export function ProgramDetail() {

    const HIDE_TEXT = false; // Cambiar f o t
     

    const { programId } = useParams();
    const navigate = useNavigate();
    const [programData, setProgramData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [overlayLoading, setOverlayLoading] = useState(false);
    const [otList, setOtList] = useState([]);
    const [timelineItems, setTimelineItems] = useState([]);
    const [showTimeline, setShowTimeline] = useState(false); // Control para mostrar el timeline
    const [timelineLoading, setTimelineLoading] = useState(false);
    const [timelineGroups, setTimelineGroups] = useState([]);
    const [timelineMode, setTimelineMode] = useState('planning'); // 'planning' o 'execution'

    const [expandedOTs, setExpandedOTs] = useState({});
    const [maquinas, setMaquinas] = useState([]);

    const [pendingChanges, setPendingChanges] = useState({});
    const [savingChanges, setSavingChanges] = useState(false);
    const [maquinasPorProceso, setMaquinasPorProceso] = useState({});


    // Para controlar la visibiidad de la alerta de cambios pendientes
    const [showPendingChangesAlert, setShowPendingChangesAlert] = useState(false);

    const [showAgregarOrden, setShowAgregarOrden] = useState(false);

    const [showReajustesModal, setShowReajustesModal] = useState(false);
    const [ajustes, setAjustes] = useState(null);

    const [isAdmin, setIsAdmin] = useState(false);

    const [showTimelineTimeReal, setShowTimelineTimeReal] = useState(false);

    // NUEVO: Estados para modal de progreso
    const [showProgressModal, setShowProgressModal] = useState(false);
    const [selectedItemRuta, setSelectedItemRuta] = useState(null);
    const [selectedOtData, setSelectedOtData] = useState(null);
    
    // NUEVO: Estados para reagendamiento
    const [showReagendarModal, setShowReagendarModal] = useState(false);
    const [previewReagendamiento, setPreviewReagendamiento] = useState(null);

    // ✅ AGREGAR ESTOS ESTADOS
    const [showAnalisisAvances, setShowAnalisisAvances] = useState(false);
    const [selectedOtAnalisis, setSelectedOtAnalisis] = useState(null);
    const [otsConInconsistencias, setOtsConInconsistencias] = useState([]);

    // Agregar estado:
    const [showInconsistencias, setShowInconsistencias] = useState(false);
    


    useEffect(() => {
        const { user } = checkAuthStatus();
        setIsAdmin(user?.is_staff || false);
    }, []);

    //Agregar función para cargar máquinas por proceso
    const cargarMaquinasPorProceso = async (itemRuta) => {
        try{
            console.log("[Frontend] itemRuta completo:", itemRuta);

            //Verificar si el objecto tiene la propiedad codigo_proceso
            if(!itemRuta || !itemRuta.codigo_proceso){
                console.error("[Frontend] Error: itemRuta no tiene codigo_proceso", itemRuta);
                return [];
            }
            const codigoProceso = itemRuta.codigo_proceso;
            console.log(`[Frontend] Código de proceso extraído: ${codigoProceso}`);

            //Verificar que el código de proceso no sea null o undefined
            if(!codigoProceso){
                console.error('[Frontend] No se encontró código de proceso para el item:', itemRuta);
                return [];
            }
            console.log(`[Frontend] Llamando a getMáquinas con programId=${programId}, procesoCodigo=${codigoProceso} `);
            const maquinasData = await getMaquinas(programId, codigoProceso);

            console.log(`[Frontend] Máquinas recibidas para proceso ${codigoProceso}:`, maquinasData);
            setMaquinasPorProceso(prev => ({
                ...prev,
                [itemRuta.id]: maquinasData
            }));
            return maquinasData;
        } catch(error) {
            console.error('Error al cargar máquinas para el proceso:', error);
            toast.error("Error al cargar máquinas disponibles");
            return [];
        }
    };

    const handleProcessChange = (otId, procesoId, field, value) => {
        if(!otList){
            console.error('otList no está inicializado.');
            return;
        }
    
        console.log(`Cambio pendiente en OT: ${otId}, Proceso: ${procesoId}, Campo: ${field}, Valor: ${value}`);
    
        setOtList(prevOtList => {
            if(!prevOtList) return [];  // Retornamos array vacío si es undefined
    
            const newList = prevOtList.map(ot => {
                if(ot.orden_trabajo === otId && ot.procesos){
                return{
                    ...ot,
                    procesos: ot.procesos.map(proceso => {
                            if(proceso.id === procesoId){
                            return {
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
        });

        setPendingChanges(prev => {
            const newChanges = {
                ...prev,
                [`${otId}-${procesoId}-${field}`]: {
                    otId,
                    procesoId,
                    field,
                    value
                }
            };
            console.log('Cambios pendientes:', newChanges);
            //Mostrar la alerta si hay cambios pendientes
            setShowPendingChangesAlert(true);

            return newChanges;
        });
    };

    const handleUpdateProductStandard = async (itemRutaId) => {
        try {
            setOverlayLoading(true);
            const result = await updateProductStandard(programId, itemRutaId);
            toast.success(`${result.message || "Estándar actualizado"}`);
        } catch (error) {
            console.error("Error al actualizar estándar:", error);
            toast.error(error.response?.data?.error || "Error al actualizar el estándar");
        } finally {
            setOverlayLoading(false);
        }
    };


    const handleSaveChanges = async () => {
        try {
            setSavingChanges(true);
            setOverlayLoading(true);
            console.log("Guardando cambios:", pendingChanges);

            //Procesar cambios en procesos (estandar, cantidad, maquina)
            const procesosConCambios = {};

            //Agrupar cambios por ot y proceso
            Object.keys(pendingChanges).forEach(key => {
                if (!key.includes('_asignacion')){
                    const [otId, procesoId, field] = key.split('-');

                    if (!procesosConCambios[otId]){
                        procesosConCambios[otId] = {};
                    }

                    if (!procesosConCambios[otId][procesoId]) {
                        procesosConCambios[otId][procesoId] = {};
                    }

                    procesosConCambios[otId][procesoId][field] = pendingChanges[key].value;
                }
            });

            
            // Procesar cambios de prioridad
            const orderIds = otList.map((ot, index) => {
                const procesos = [];

                if (procesosConCambios[ot.orden_trabajo]){
                    Object.keys(procesosConCambios[ot.orden_trabajo]).forEach(procesoId => {
                        procesos.push({
                            id: parseInt(procesoId),
                            ...procesosConCambios[ot.orden_trabajo][procesoId]
                        });
                    });
                }

                return {
                    id: ot.orden_trabajo,
                    priority: index + 1 ,
                    procesos: procesos.length > 0 ? procesos: undefined
                }
            });
            
            if (orderIds.length > 0) {
                console.log("Actualizando prioridades:", orderIds);
                await updatePriorities(programId, orderIds, true);
            }
            
            // Limpiar cambios pendientes
            setPendingChanges({});

            //Ocultar la alerta después de guardar
            setShowPendingChangesAlert(false);
            
            // Recargar datos
            await fetchProgramData();
            
            // Recargar timeline si está visible
            if (showTimeline) {
                loadTimelineData();
            }
            
            toast.success("Cambios guardados correctamente");
        } catch (error) {
            console.error("Error al guardar los cambios:", error);
            toast.error(`Error al guardar los cambios: ${error.message}`);
        } finally {
            setSavingChanges(false);
            setOverlayLoading(false);
        }
    };

    const handleToggleExpand = async(otId) => {
        const expandiendo = !expandedOTs[otId];
        setExpandedOTs((prevExpanded) => ({
            ...prevExpanded,
            [otId]: expandiendo
        }));

        //Si estamos expandiendo, cargar las máquinas para cada proceso
        if(expandiendo){
            const ot = otList.find(ot => ot.orden_trabajo === otId);
            if (ot && ot.procesos){ 
                for (const proceso of ot.procesos) { 
                    if(!maquinasPorProceso[proceso.id]){
                        await cargarMaquinasPorProceso(proceso);
                    }
                }
            }
        }
    };

    const toggleTimeline = () => {
        if (hayProcesosConEstandarCero()) {
            const procesosConEstandarCero = getProcesosConEstandarCero();

            toast.error(
                <div>
                    <p>No se puede proyectar: Hay procesos con estándar en 0</p>
                    <ul style={{ maxHeight: '200px', overflowY: 'auto', padding: '0 0 0 20px'}}>
                        {procesosConEstandarCero.map((p, idx) => (
                            <li key={idx}>{p.ot_codigo} - {p.proceso_descripcion}</li>
                        ))}
                    </ul>
                    <p>Por favor, corrija los valores antes de proyectar.</p>
                </div>,
                { duration: 5000 }
            );
            return; //Salimos de la función sin cambiar el estado del timeline
        }

        //Solo llegamos aquí si no hay procesos con estándar en 0
        if (!showTimeline) {
            setTimelineLoading(true);
            setTimeout(() => setTimelineLoading(false), 1000); // Simula carga
        }
        setShowTimeline(!showTimeline);
    };


    const fetchData = async () => {
        if(!programId){
            console.error("No hay programId disponible");
            return;
        }
        try{
            const maquinasData = await getMaquinas(programId);
            setMaquinas(maquinasData);    
        }catch(error){
            console.error("Error al cargar datos:", error);
            toast.error("Error al cargar las maquinas");
        }
    };

    const fetchProgramData = async () => {
        setLoading(true);
        try {
            const response = await getProgram(programId);
            console.log("Datos recibidos del backend:", response.data);
            
            setProgramData({
                ...(response.program || {}),
                routes_data: response.routes_data
            });
            
            // Procesar las órdenes de trabajo y sus asignaciones
            const ordenesTrabajo = response.ordenes_trabajo || [];
            setOtList(ordenesTrabajo);

            // Validar y procesar los datos del timeline
            console.log("response del backnd: ", response.routes_data)
            if (response.routes_data && typeof response.routes_data === "object") {
                const groups = response.routes_data.groups;
                const items = response.routes_data.items;

                // Procesar grupos y subgrupos
                if (Array.isArray(groups)) {
                    const flatGroups = groups.flatMap(ot => {
                        // Grupo principal (OT)
                        const mainGroup = {
                            id: ot.id,
                            title: ot.orden_trabajo_codigo_ot || "OT Sin código",
                            stackItems: true,
                            height: 70
                        };

                        // Subgrupos (procesos)
                        const processGroups = ot.procesos?.map(proceso => ({
                            id: `${ot.id}-${proceso.id}`,
                            title: proceso.descripcion || "Sin descripción",
                            height: 50,
                            parent: ot.id
                        })) || [];

                        return [mainGroup, ...processGroups];
                    });

                    setTimelineGroups(flatGroups);
                }

                // Procesar items del timeline
                if (Array.isArray(items)) {
                    const timelineItems = items.map((item) => {
                        // Determinar el color basado en el estado y asignación
                        let backgroundColor;
                        if (item.asignado) {
                            backgroundColor = "#4CAF50"; // Verde si tiene asignación
                        } else if (new Date(item.end_time) < new Date()) {
                            backgroundColor = "#ff4444"; // Rojo si está vencido
                        } else {
                            backgroundColor = "#FFA726"; // Naranja por defecto
                        }

                        return {
                            id: item.id,
                            group: `${item.ot_id}-${item.proceso_id}`,
                            title: `${item.name}${item.operador_nombre ? ` - Op: ${item.operador_nombre}` : ''}`,
                            start_time: new Date(item.start_time),
                            end_time: new Date(item.end_time),
                            itemProps: {
                                style: {
                                    backgroundColor,
                                    color: 'white',
                                    borderRadius: '4px',
                                    padding: '2px 6px',
                                    fontSize: '12px'
                                },
                                'data-tooltip': `
                                    ${item.name}
                                    Cantidad: ${item.cantidad_intervalo} de ${item.cantidad_total}
                                    ${item.operador_nombre ? `Operador: ${item.operador_nombre}` : 'Sin operador asignado'}
                                    ${item.maquina_codigo ? `Máquina: ${item.maquina_codigo} - ${item.maquina_descripcion}` : 'Sin máquina asignada'}
                                    Estándar: ${item.estandar} u/hr
                                    Inicio: ${new Date(item.start_time).toLocaleString()}
                                    Fin: ${new Date(item.end_time).toLocaleString()}
                                `
                            },
                            canMove: false,
                            canResize: false
                        };
                    });
                    setTimelineItems(timelineItems);
                }
            }

            // Después de recibir los datos de planificación
            console.log("Datos completos de planificación:", response);
            if (response && response.groups) {
                response.groups.forEach((group, index) => {
                    console.log(`Grupo ${index} (${group.id}):`, group);
                    if (group.procesos) {
                        console.log(`  Número de procesos: ${group.procesos.length}`);
                        group.procesos.forEach(proceso => {
                            console.log(`  - Proceso ${proceso.id}: ${proceso.descripcion}`);
                        });
                    } else {
                        console.log(`  No tiene procesos definidos`);
                    }
                });
            }
        } catch (error) {
            console.error("Error al cargar detalles del programa:", error);
            toast.error("Error al cargar los datos");
        } finally {
            setLoading(false);
        }
    };

    const loadTimelineData = async () => {
        if (!showTimeline || !programId) return;
        
        try {
            setTimelineLoading(true);
            let timelineData;

            if (timelineMode === 'execution') {
                console.log("Cargando datos de ejecución...");
                //const response = await supervisorReportAPI.getExecutionTimeline(programId);
                const response = '';
                console.log("Datos de ejecución recibidos:", response);
                
                // Transformar los datos de ejecución al formato esperado
                timelineData = {
                    groups: response.routes_ || [],
                    items: response.items || []
                };
            } else {
                console.log("Cargando datos de planificación...");
                console.log("🔍 DEBUG PLANIFICACIÓN:", {
                    tieneProgramData: !!programData,
                    tieneRoutesData: !!programData?.routes_data,
                    routesDataGroups: programData?.routes_data?.groups?.length || 0,
                    routesDataItems: programData?.routes_data?.items?.length || 0,
                    estructuraCompleta: programData?.routes_data
                });
                // Usar los datos de routes_data que ya tenemos en programData
                if (programData && programData.routes_data) {
                    console.log("Usando datos de planificación de routes_data", programData.routes_data);
                    timelineData = programData.routes_data;
                } else {
                    // Si no tenemos los datos, obtenerlos de nuevo
                    const response = await getProgram(programId);
                    console.log("Datos de planificación recibidos:", response);
                    timelineData = response.routes_data || { groups: [], items: [] };
                 }
            }

            processTimelineData(timelineData);
        } catch (error) {
            console.error('Error cargando datos del timeline:', error);
            toast.error('Error al cargar la proyección');
        } finally {
            setTimelineLoading(false);
        }
    };

    useEffect(() => {
        if (showTimeline) {
            console.log("Modo timeline cambiado a:", timelineMode);
            loadTimelineData();
        }
    }, [showTimeline, timelineMode, programId]);

    const processTimelineData = (timelineData) => {
        console.log("Datos recibidos en processTimelineData:", timelineData);

        if (!timelineData.groups || !timelineData.items) {
            console.error("Datos de timeline inválidos:", timelineData);
                setTimelineGroups([]);
                setTimelineItems([]);
                return;
            }

        // Determinar si estamos en modo planificación o ejecución
        const isExecutionMode = timelineMode === 'execution';
                
        // 1. Procesar los grupos y sus procesos
        let processedGroups = [];
        
        // Crear un mapa de procesos únicos por OT basado en los items
        const procesosUnicos = {};
        
        // Extraer los procesos únicos de los items
        timelineData.items.forEach(item => {
            if (!procesosUnicos[item.ot_id]) {
                procesosUnicos[item.ot_id] = {};
            }
            
            // Agregar este proceso si no existe ya
            if (!procesosUnicos[item.ot_id][item.proceso_id]) {
                procesosUnicos[item.ot_id][item.proceso_id] = {
                    id: item.proceso_id,
                    title: item.name.split(' - ')[0], // Extraer el nombre del proceso
                    parent: item.ot_id
                };
            }
        });
        
        // Recorrer cada grupo (OT)
        timelineData.groups.forEach(ot => {
            // Crear grupo principal para la OT
                const mainGroup = {
                id: ot.id,
                title: typeof ot.orden_trabajo_codigo_ot === 'number' 
                    ? `OT ${ot.orden_trabajo_codigo_ot}` 
                    : ot.orden_trabajo_codigo_ot  || `OT ${ot.id}`,
                    stackItems: true,
                    height: 70
                };

            processedGroups.push(mainGroup);
            
            // Agregar todos los procesos encontrados para esta OT
            const procesosOT = procesosUnicos[ot.id] || {};
            
            Object.values(procesosOT).forEach(proceso => {
                processedGroups.push({
                    id: proceso.id,
                    title: proceso.descripcion,
                    parent: ot.id,
                    height: 50
                });
            });
        });
        
        // 2. Procesar los items con formato unificado
        const processedItems = timelineData.items.map(item => {
            id: item.id;
            group: item.proceso_id;
            title: item.title || item.name || '';
            start_time: moment(item.start_time).toDate();
            let backgroundColor = '#9E9E9E';
            let borderStyle = 'solid';
            let borderWidth = '1px';
            
            const esContinuacion = item.es_continuacion === true;
            const esTemporal = item.es_temporal === true;
            
            switch (item.estado?.toUpperCase()) {
                case 'COMPLETADO':
                    backgroundColor = '#4CAF50';
                    break;
                case 'EN_PROCESO':
                    backgroundColor = '#2196F3';
                    break;
                case 'CONTINUADO':
                    backgroundColor = '#FF9800';
                    borderStyle = 'dashed';
                    borderWidth = '2px';
                    break;
                case 'DETENIDO':
                    backgroundColor = '#F44336';
                    break;
                default:
                    backgroundColor = isExecutionMode ? '#9E9E9E' : '#FFA726';
            }
            
            if (esTemporal) {
                borderStyle = 'dotted';
            }
            
            if (esContinuacion) {
                borderStyle = 'dashed';
                borderWidth = '2px';
            }
            
            return {
                id: item.id,
                group: item.proceso_id,
                title: item.title || item.name || '',
                start_time: moment(item.start_time).toDate(),
                end_time: moment(item.end_time).toDate(),
                className: `timeline-item ${item.estado?.toLowerCase() || 'pendiente'} ${esContinuacion ? 'continuacion' : ''} ${esTemporal ? 'temporal' : ''}`,
                itemProps: {
                    style: {
                        backgroundColor,
                        color: 'white',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '12px',
                        borderStyle,
                        borderWidth
                    },
                    'data-tooltip': `
                        ${item.title || item.name || ''}
                        ${esContinuacion ? '(Continuación)' : ''}
                        ${esTemporal ? '(Proyectado)' : ''}
                        Estado: ${item.estado || 'Pendiente'}
                        Cantidad: ${item.cantidad_intervalo} de ${item.cantidad_total} unidades
                        ${typeof item.porcentaje_avance !== 'undefined' ? `Avance: ${parseFloat(item.porcentaje_avance).toFixed(1)}%` : ''}
                        Inicio: ${moment(item.start_time).format('DD/MM/YYYY HH:mm')}
                        Fin: ${moment(item.end_time).format('DD/MM/YYYY HH:mm')}
                    `
                }
            };
        });

        console.log('📊 DATOS PROCESADOS PARA TIMELINE:', {
            processedGroups: processedGroups,
            processedItems: processedItems,
            cantidadGrupos: processedGroups.length,
            cantidadItems: processedItems.length,
            primerosGrupos: processedGroups.slice(0, 3),
            primerosItems: processedItems.slice(0, 3)
        });

        setTimelineGroups(processedGroups);
        setTimelineItems(processedItems);
    };

    // Función auxiliar para determinar el color según el estado
    const getEstadoColor = (estado) => {
        switch (estado?.toUpperCase()) {
            case 'COMPLETADO': return '#4CAF50';
            case 'EN_PROCESO': return '#2196F3';
            case 'DETENIDO': return '#f44336';
            default: return '#FFA726';
        }
    };

    useEffect(()=> {  
        fetchData();
    }, [programId])

    useEffect(() => {
        if (!programId) {
            console.error("No se proporcionó un programId");
            return;
        }
        fetchProgramData();
        cargarOTsConInconsistencias();
    }, [programId]);
    
    const handleDeleteOrder = async (orderId) => {
        console.log(orderId, programId);
        if(window.confirm("¿Estás seguro que deseas eliminar esta orden de trabajo?")){
            setLoading(true);
            try{
                const result = await deleteOrder(programId, orderId);
                if(result && result.deleted > 0){
                setOtList(otList.filter((ot) => ot.orden_trabajo !== orderId));
                console.log("Orden de trabajo eliminada exitósamente.");
                }else{
                    console.error("Error al eliminar la orden de trabajo:", result);
                    alert("No se pudo eliminar la orden de trabajo");
                }
            }catch(error){
                console.error("Error al eliminar la orden de trabajo:", error);
                alert(error.message ||"Error al eliminar la orden de trabajo");
            }finally{
                setLoading(false);
            }
        }
    };

    const handleOtReorder = (newOtList) => {
        console.log("Nueva lista recibida: ", newOtList);
        setOtList(newOtList);

        const updatedGroups = newOtList.flatMap(ot => {
            const mainGroup = {
                id: `ot_${ot.orden_trabajo}`,
                title: ot.orden_trabajo_codigo_ot,
                height: 50,
                stackItems: true
            };

            const processGroups = ot.procesos.map(proceso => ({
                id: `${mainGroup.id}-${proceso.id}`,
                title: proceso.descripcion,
                parent: mainGroup.id,
                height: 30
            }));

            return [mainGroup, ...processGroups];
        });

        setTimelineGroups(updatedGroups);

        const orderIds = newOtList.map((ot, index) => ({
                id: ot.orden_trabajo,
                priority: index + 1
        })).filter(item => item !== null);

        console.log("Actualizando prioridades: ", orderIds);
        setLoading(true);

        updatePriorities(programId, orderIds)
            .then((response) => {
                console.log("Prioridades actualizadas:", response);

                if (response.routes_data?.items) {
                    const serverItems = response.routes_data.items.map(item => ({
                        id: item.id,
                        group: `${item.ot_id}-${item.proceso_id}`,
                        title: `${item.name} (Restantes: ${item.unidades_restantes})`,
                        start_time: new Date(item.start_time + 'Z'),
                        end_time: new Date(item.end_time + 'Z'),
                        itemProps: {
                            style: {
                                backgroundColor: '#4CAF50',
                                color: 'white',
                                borderRadius: '4px',
                                padding: '2px 6px',
                                opacity: 1 - (item.unidades_restantes / item.cantidad_total)
                            }
                        }
                    }));
                    setTimelineItems(serverItems);
                }
                
                // Recargar la vista de ejecución si estamos en ese modo
                if (timelineMode === 'execution' && showTimeline) {
                    loadTimelineData();
                }
            })
            .catch((error) => {
                console.error("Error al actualizar prioridades", error);
                alert("Error al actualizar el orden de las OTs");
            })
            .finally(() => {
                setLoading(false);
            });
    };

    const hayProcesosConEstandarCero =() => {
        if (!otList || otList.length === 0) return false;

        return otList.some(ot => 
            ot.procesos && ot.procesos.some(proceso => 
                !proceso.estandar || parseFloat( proceso.estandar) === 0
            )
        );
    };

    const getProcesosConEstandarCero = () => {
        const procesosConEstandarCero = [];

        otList?.forEach( ot => {
            ot.procesos?.forEach(proceso => {
                if (!proceso.estandar || parseFloat(proceso.estandar) === 0) {
                    procesosConEstandarCero.push({
                        ot_codigo: ot.orden_trabajo_codigo_ot,
                        proceso_descripcion: proceso.descripcion,
                        id: proceso.id
                    });
                }
            });
        });

        return procesosConEstandarCero;
    };

    // NUEVO: Manejar click en proceso para abrir modal de progreso
    const handleProcessClick = (itemRuta, otData) => {
        setSelectedItemRuta(itemRuta);
        setSelectedOtData(otData);
        setShowProgressModal(true);
    };

    // NUEVO: Manejar actualización de progreso
    const handleProgressUpdated = (updatedData) => {
        // Actualizar la lista local de OTs
        setOtList(prevOtList => 
            prevOtList.map(ot => {
                if (ot.orden_trabajo === selectedOtData.orden_trabajo) {
                    return {
                        ...ot,
                        procesos: ot.procesos.map(proceso => 
                            proceso.id === selectedItemRuta.id 
                                ? { 
                                    ...proceso, 
                                    cantidad_terminado_proceso: updatedData.cantidad_terminado_proceso,
                                    porcentaje_completado: updatedData.porcentaje_completado,
                                    cantidad_pendiente: updatedData.cantidad_pendiente,
                                    estado_proceso: updatedData.estado_proceso,
                                    fecha_inicio_real: updatedData.fecha_inicio_real,
                                    fecha_fin_real: updatedData.fecha_fin_real,
                                    operador_actual: updatedData.operador_actual,
                                    observaciones_progreso: updatedData.observaciones_progreso,
                                    ultima_actualizacion: updatedData.ultima_actualizacion
                                }
                                : proceso
                        ),
                        // Actualizar avance de la OT si es necesario
                        ...(updatedData.orden_trabajo && updatedData.orden_trabajo.cantidad_avance && {
                            avance_ot: updatedData.orden_trabajo.cantidad_avance 
                        })
                    };
                }
                return ot;
            })
        );

        // Mostrar mensaje de éxito
        if (updatedData.es_ultimo_proceso_ot && updatedData.porcentaje_completado >= 100) {
            toast.success(`¡Proceso completado! ${updatedData.orden_trabajo?.codigo_ot || ''}`);
        } else {
            toast.success('Progreso actualizado correctamente');
        }
        
        // Recargar timeline si está visible
        if (showTimeline) {
            loadTimelineData();
        }

        setSelectedItemRuta(null);
        setSelectedOtData(null);
    };

    // NUEVO: Previsualizar reagendamiento
    const handlePreviewReagendamiento = async () => {
        try {
            const preview = await previewReagendarPrograma(programId);
            setPreviewReagendamiento(preview);
            setShowReagendarModal(true);
        } catch (error) {
            toast.error("Error al calcular reagendamiento");
        }
    };

    // ✅ AGREGAR ESTA FUNCIÓN
    const cargarOTsConInconsistencias = async () => {
        try {
            const response = await axios.get(`/gestion/api/v1/programas/${programId}/ots-inconsistencias/`);
            setOtsConInconsistencias(response.data.ots);
        } catch (error) {
            console.error('Error cargando OTs con inconsistencias:', error);
        }
    };

    const renderOt = (ot) => {
        const hasPendingChanges = Object.keys(pendingChanges).some(key => 
            key.startsWith(`${ot.orden_trabajo}-`)
        );
        
        // ✅ NUEVA LÓGICA: Verificar si esta OT tiene inconsistencias
        const otInconsistencias = otsConInconsistencias.find(
            otInc => otInc.ot_id === ot.orden_trabajo
        );
        const tieneInconsistencias = otInconsistencias?.inconsistencias?.length > 0;
        const tieneAvanceHistorico = otInconsistencias?.tiene_avance_historico;

        const maquinasPrincipales = ot.procesos
            ?.filter(p => p.maquina_codigo)
            ?.map(p => `${p.maquina_codigo}`)
            ?.filter((value, index, self) => self.indexOf(value) === index) // Únicos
            ?.slice(0, 3); // Máximo 3

        return (
            <Card 
                key={ot.orden_trabajo}
                className={`ot-card mb-3 ${expandedOTs[ot.orden_trabajo] ? 'expanded' : ''}`}
            >
                <Card.Header className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center">
                        <div className="ot-number me-3">
                            <h6 className="mb-0">#{ot.orden_trabajo_codigo_ot}</h6>
                            <div className="d-flex gap-1 mt-1">
                                {/* ✅ BADGES SIMPLIFICADOS */}
                                {tieneAvanceHistorico && (
                                    <Badge bg="info" size="sm">📊 Histórico</Badge>
                                )}
                                {tieneInconsistencias && (
                                    <Badge bg="warning" size="sm">⚠️ Inconsistencias</Badge>
                                )}
                            </div>
                        </div>
                        <div className="ot-info">
                            <h6 className="mb-1">{ot.orden_trabajo_descripcion_producto_ot}</h6>
                            <div className="d-flex gap-3">
                            <small className="text-muted">
                                <FaCalendarAlt className="me-1" />
                                {ot.orden_trabajo_fecha_termino}
                            </small>
                                {/* ✅ RESUMEN SIMPLIFICADO */}
                                {otInconsistencias && (
                                    <small className={tieneInconsistencias ? "text-warning" : "text-info"}>
                                        OT: {otInconsistencias.avance_ot} | 
                                        Último: {otInconsistencias.avance_procesos}
                                        {Math.abs(otInconsistencias.diferencia) > 0.01 && (
                                            <span className="fw-bold ms-1">
                                                (Δ{otInconsistencias.diferencia.toFixed(0)})
                                            </span>
                                        )}
                                    </small>
                                )}
                                {/* ✅ NUEVO: Mostrar máquinas principales */}
                                {maquinasPrincipales && maquinasPrincipales.length > 0 && (
                                    <small className="text-info">
                                        🏭 {maquinasPrincipales.join(', ')}
                                        {ot.procesos?.filter(p => p.maquina_codigo).length > 3 && ' +...'}
                                    </small>
                                )}
                        </div>
                    </div>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                        {/* ✅ BOTÓN PRINCIPAL DE ANÁLISIS */}
                        {(tieneAvanceHistorico || tieneInconsistencias) && (
                            <Button
                                variant={tieneInconsistencias ? "warning" : "info"}
                                size="sm"
                                onClick={() => {
                                    setSelectedOtAnalisis(ot);
                                    setShowAnalisisAvances(true);
                                }}
                                title={tieneInconsistencias ? "Resolver inconsistencias de avance" : "Analizar avances históricos"}
                            >
                                {tieneInconsistencias ? '⚠️ Resolver' : '📊 Analizar'}
                            </Button>
                        )}
                        
                        {/* ✅ BOTÓN GUARDAR SOLO SI HAY CAMBIOS */}
                        {hasPendingChanges && (
                            <Button
                                variant="success"
                                size="sm"
                                onClick={handleSaveChanges}
                                disabled={savingChanges}
                            >
                                <FaSave className="me-1" />
                                {savingChanges ? "Guardando..." : "Guardar"}
                            </Button>
                        )}
                        
                        {/* ✅ BOTÓN EXPANDIR/CONTRAER */}
                        <Button
                            variant={expandedOTs[ot.orden_trabajo] ? "primary" : "outline-primary"}
                            size="sm"
                            onClick={() => handleToggleExpand(ot.orden_trabajo)}
                        >
                            <FaChevronDown 
                                className={`transition-transform ${
                                    expandedOTs[ot.orden_trabajo] ? 'rotate-180' : ''
                                }`}
                            />
                        </Button>
                    </div>
                </Card.Header>

                <Collapse in={expandedOTs[ot.orden_trabajo]}>
                    <Card.Body className="p-0">
                        <div className="table-responsive">
                            <Table className="process-table mb-0">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Proceso</th>
                                        <th>Máquina Actual</th>
                                        <th>Máquina Disponible</th>
                                        <th>Cantidad Total</th>
                                        <th className="text-center">Completado</th>
                                        <th className="text-center">Restante</th>
                                        <th>Estándar</th>
                                        <th className="text-center">Estado</th>
                                        <th className="text-center">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {ot.procesos?.map((item_ruta) => {
                                        const cantidadTotal = parseFloat(item_ruta.cantidad || 0);
                                        const cantidadTerminada = parseFloat(item_ruta.cantidad_terminado_proceso || 0);
                                        const cantidadRestante = Math.max(0, cantidadTotal - cantidadTerminada);
                                        const porcentajeReal = cantidadTotal > 0 ? (cantidadTerminada / cantidadTotal) * 100 : 0;
                                        
                                        // ✅ VERIFICAR SI HAY INCONSISTENCIAS PARA ESTE PROCESO
                                        const inconsistenciaOT = otsConInconsistencias.find(otInc => otInc.ot_id === ot.orden_trabajo);
                                        const tieneInconsistencias = inconsistenciaOT?.inconsistencias?.length > 0;
                                        
                                        // ✅ DETERMINAR ESTADO REAL
                                        const estaCompleto = porcentajeReal >= 100;
                                        const tieneSobreAvance = cantidadTerminada > cantidadTotal;
                                        const tieneAvance = cantidadTerminada > 0;
                                        
                                        // ✅ LÓGICA CORREGIDA: No planificar si hay inconsistencias o está completo
                                        const incluyeEnPlanificacion = cantidadRestante > 0 && !estaCompleto && !tieneInconsistencias;
                                        
                                        return (
                                        <tr 
                                            key={item_ruta.id}
                                                className={`
                                                    ${!item_ruta.estandar || parseFloat(item_ruta.estandar) === 0 ? "table-danger" : ""} 
                                                    ${estaCompleto ? "table-success" : ""}
                                                    ${tieneSobreAvance ? "table-warning" : ""}
                                                    ${tieneInconsistencias ? "table-info" : ""}
                                                `}
                                                title={
                                                    tieneInconsistencias ? "⚠️ OT con inconsistencias - Resolver antes de planificar" :
                                                    estaCompleto ? "✅ Proceso completado - No se incluirá en planificación" :
                                                    tieneSobreAvance ? "⚠️ Proceso con sobre-avance - Revisar datos" :
                                                    tieneAvance ? "🔄 Proceso con avance parcial - Se planificará el restante" :
                                                    "📋 Proceso sin avance - Se planificará completo"
                                                }
                                            >
                                                <td>
                                                    <div className="d-flex align-items-center">
                                                        <span className="fw-bold">{item_ruta.item}</span>
                                                        {/* ✅ INDICADORES SIMPLIFICADOS */}
                                                        {tieneInconsistencias && <Badge bg="warning" className="ms-2" size="sm">⚠️</Badge>}
                                                        {estaCompleto && <Badge bg="success" className="ms-2" size="sm">✅</Badge>}
                                                        {tieneSobreAvance && <Badge bg="danger" className="ms-2" size="sm">⚠️</Badge>}
                                                    </div>
                                                </td>
                                                <td>
                                                    <div>
                                                        <strong>{item_ruta.codigo_proceso}</strong>
                                                        <br />
                                                        <small className="text-muted">{item_ruta.descripcion}</small>
                                                    </div>
                                            </td>
                                            <td>
                                                {item_ruta.maquina_codigo ? (
                                                    <div>
                                                        <strong className="text-primary">{item_ruta.maquina_codigo}</strong>
                                                        <br />
                                                        <small className="text-muted">{item_ruta.maquina_descripcion}</small>
                                                    </div>
                                                ) : (
                                                    <Badge bg="warning" className="d-block text-center">
                                                        Sin asignar
                                                    </Badge>
                                                )}
                                            </td>
                                            <td>
                                                <select 
                                                    className="form-select form-select-sm" 
                                                    value={item_ruta.maquina_id || ''}
                                                    onChange={(e) => handleProcessChange(
                                                        ot.orden_trabajo,
                                                        item_ruta.id,
                                                        "maquina_id",
                                                        e.target.value
                                                    )}
                                                    disabled={estaCompleto || tieneInconsistencias}
                                                    onFocus={(e) => {
                                                        if(!maquinasPorProceso[item_ruta.id]){
                                                            cargarMaquinasPorProceso(item_ruta);
                                                        }
                                                    }}
                                                >
                                                    <option value="">Seleccionar máquina</option>
                                                    {(maquinasPorProceso[item_ruta.id] || maquinas).map(maquina => (
                                                            <option value={maquina.id} key={maquina.id}>
                                                                {maquina.codigo_maquina} - {maquina.descripcion || 'Sin descripción'}
                                                        </option>
                                                    ))}
                                                </select>
                                                {/* ✅ Ayuda visual */}
                                                <small className="text-muted d-block mt-1">
                                                    {(maquinasPorProceso[item_ruta.id] || maquinas).length} máquinas disponibles
                                                </small>
                                            </td>
                                                <td className="text-center">
                                                    <div className="d-flex flex-column align-items-center">
                                                        <strong>{cantidadTotal.toLocaleString()}</strong>
                                                        <Form.Control 
                                                            type="number" 
                                                            size="sm"
                                                            style={{ width: '80px' }}
                                                            value={item_ruta.estandar || 0}
                                                            onChange={(e) => {
                                                                handleProcessChange(
                                                                    ot.orden_trabajo,
                                                                    item_ruta.id,
                                                                    'estandar',
                                                                    parseFloat(e.target.value)
                                                                );
                                                            }}
                                                            disabled={estaCompleto || tieneInconsistencias}
                                                            className={!item_ruta.estandar || parseFloat(item_ruta.estandar) === 0 ? "border-danger" : ""}
                                                        />
                                                    </div>
                                                </td>
                                                
                                                {/* ✅ COLUMNA COMPLETADO SIMPLIFICADA */}
                                                <td className="text-center">
                                                    <div className="d-flex flex-column align-items-center">
                                                        <strong className={`
                                                            fs-6 ${tieneAvance ? 'text-primary' : 'text-muted'}
                                                            ${tieneSobreAvance ? 'text-warning' : ''}
                                                        `}>
                                                            {cantidadTerminada.toLocaleString()}
                                                        </strong>
                                                        <div className="progress mt-1" style={{ width: '60px', height: '8px' }}>
                                                            <div 
                                                                className={`progress-bar ${
                                                                    porcentajeReal >= 100 ? 'bg-success' : 
                                                                    porcentajeReal >= 50 ? 'bg-primary' : 'bg-warning'
                                                                }`}
                                                                style={{ width: `${Math.min(porcentajeReal, 100)}%` }}
                                                            ></div>
                                                        </div>
                                                        <small className="text-muted">{porcentajeReal.toFixed(0)}%</small>
                                                    </div>
                                                </td>
                                                
                                                {/* ✅ COLUMNA RESTANTE SIMPLIFICADA */}
                                                <td className="text-center">
                                                    <div className="d-flex flex-column align-items-center">
                                                        <strong className={`
                                                            fs-6 ${cantidadRestante > 0 ? 'text-info' : 'text-success'}
                                                        `}>
                                                            {cantidadRestante.toLocaleString()}
                                                        </strong>
                                                        <Badge 
                                                            bg={incluyeEnPlanificacion ? 'primary' : 'secondary'} 
                                                            className="mt-1"
                                                            style={{ fontSize: '0.7rem' }}
                                                        >
                                                            {incluyeEnPlanificacion ? '📋 Planificar' : 
                                                             tieneInconsistencias ? '⚠️ Revisar' : 
                                                             '✓ Completo'}
                                                        </Badge>
                                                    </div>
                                                </td>
                                                
                                                <td className="text-center">
                                                    <Form.Control 
                                                    type="number" 
                                                        size="sm"
                                                        style={{ width: '80px' }}
                                                        value={item_ruta.estandar || 0}
                                                        onChange={(e) => {
                                                            handleProcessChange(
                                                                ot.orden_trabajo,
                                                                item_ruta.id,
                                                                'estandar',
                                                                parseFloat(e.target.value)
                                                            );
                                                        }}
                                                        disabled={estaCompleto || tieneInconsistencias}
                                                        className={!item_ruta.estandar || parseFloat(item_ruta.estandar) === 0 ? "border-danger" : ""}
                                                    />
                                                </td>
                                                
                                                <td className="text-center">
                                                    <Form.Select
                                                        size="sm"
                                                        value={item_ruta.estado_proceso || 'PENDIENTE'}
                                                        onChange={(e) => handleEstadoChange(item_ruta.id, e.target.value)}
                                                        className={`estado-${(item_ruta.estado_proceso || 'PENDIENTE').toLowerCase()}`}
                                                        disabled={tieneInconsistencias}
                                                        style={{ fontSize: '0.8rem' }}
                                                    >
                                                        <option value="PENDIENTE">🟡 Pendiente</option>
                                                        <option value="EN_PROCESO">🔵 En Proceso</option>
                                                        <option value="COMPLETADO">🟢 Completado</option>
                                                        <option value="PAUSADO">🟠 Pausado</option>
                                                    </Form.Select>
                                                </td>
                                                
                                                <td className="text-center">
                                                    <div className="d-flex flex-column gap-1 align-items-center">
                                                        {/* ✅ BOTÓN PRINCIPAL SIMPLIFICADO */}
                                                        <Button 
                                                            variant={tieneInconsistencias ? "warning" : incluyeEnPlanificacion ? "primary" : "secondary"}
                                                            size="sm"
                                                            onClick={() => {
                                                                if (tieneInconsistencias) {
                                                                    setSelectedOtAnalisis(ot);
                                                                    setShowAnalisisAvances(true);
                                                                } else {
                                                                    handleProcessClick(item_ruta, ot);
                                                                }
                                                            }}
                                                            title={
                                                                tieneInconsistencias ? "Resolver inconsistencias" :
                                                                incluyeEnPlanificacion ? `Actualizar progreso` :
                                                                "Proceso completado"
                                                            }
                                                        >
                                                            {tieneInconsistencias ? '⚠️ Revisar' : 
                                                             incluyeEnPlanificacion ? '📊 Progreso' : 
                                                             '✅ OK'}
                                                        </Button>
                                                        
                                                        {/* ✅ BOTÓN RESET SOLO SI TIENE AVANCE Y NO HAY INCONSISTENCIAS */}
                                                        {tieneAvance && !tieneInconsistencias && (
                                                            <Button
                                                                variant="outline-warning"
                                                                size="sm"
                                                                onClick={() => handleResetearAvance(item_ruta.id)}
                                                                title="Resetear avance a 0"
                                                                style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem' }}
                                                            >
                                                                🔄
                                                        </Button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                            </Table>
                        </div>
                    </Card.Body>
                </Collapse>
            </Card>
        )
    };
        

    if (loading) return <LoadingSpinner message="Cargando detalles del programa..."/>;
    if (!programData) return <p>No se encontró el programa.</p>;

    const handleOrdenesAgregadas = (data) => {
        // Recargar los datos del programa
        fetchProgramData();
    };

    const verificarReajustes = async () => {
        try {
            console.log('Verificando reajustes para programa:', programId);
            const response = await verificarReajustesPrograma(programId);
            console.log('Respuesta completa:', JSON.stringify(response, null, 2));
            
            if (response.requiere_ajustes) {
                // Veamos la estructura de cada ajuste
                response.ajustes_sugeridos.forEach((ajuste, index) => {
                    console.log(`Ajuste ${index}:`, {
                        key: `${ajuste.orden_trabajo}-${ajuste.proceso.id}`,
                        orden_trabajo: ajuste.orden_trabajo,
                        proceso_id: ajuste.proceso.id,
                        fecha_propuesta: ajuste.fecha_propuesta
                    });
                });

                // Intentemos el agrupamiento de otra manera
                const ajustesUnicos = Array.from(new Set(
                    response.ajustes_sugeridos.map(ajuste => 
                        `${ajuste.orden_trabajo}-${ajuste.proceso.id}`
                    )
                )).map(key => {
                    const [ot, procesoId] = key.split('-');
                    const ajustesDeEstePar = response.ajustes_sugeridos.filter(
                        ajuste => ajuste.orden_trabajo === ot && ajuste.proceso.id === parseInt(procesoId)
                    );
                    // Tomar el último ajuste (más reciente)
                    return ajustesDeEstePar[ajustesDeEstePar.length - 1];
                });

                console.log('Ajustes únicos:', ajustesUnicos);

                setAjustes({
                    ...response,
                    ajustes_sugeridos: ajustesUnicos
                });
                setShowReajustesModal(true);
            } else {
                toast.success(response.mensaje);
            }
        } catch (error) {
            console.error('Error completo:', error);
            toast.error("Error al verificar reajustes");
        }
    };

    const aplicarReajustes = async () => {
        try {
            if (!ajustes || !ajustes.ajustes_sugeridos) {
                console.log('Estado de ajustes:', ajustes); // Agregar este log
                toast.error("No hay ajustes para aplicar");
                return;
            }
            
            console.log('Enviando ajustes:', ajustes.ajustes_sugeridos); // Agregar este log
            await aplicarReajustesPrograma(programId, ajustes.ajustes_sugeridos);
            setShowReajustesModal(false);
            toast.success("Ajustes aplicados correctamente");
            // Recargar datos del programa
            fetchProgramData();
        } catch (error) {
            console.log('Error completo:', error.response?.data); // Agregar este log
            toast.error("Error al aplicar reajustes");
            console.error(error);
        }
    };

    // MODIFICAR: Manejar cambio de estado del proceso
    const handleEstadoChange = async (itemRutaId, nuevoEstado) => {
        try {
            // Usar la nueva API específica para cambio de estado
            const updatedItemRuta = await updateItemRutaEstado(itemRutaId, nuevoEstado);

            // Actualizar el estado local
            setOtList(prevOtList => 
                prevOtList.map(ot => ({
                    ...ot,
                    procesos: ot.procesos.map(proceso => 
                        proceso.id === itemRutaId 
                            ? { 
                                ...proceso, 
                                estado_proceso: updatedItemRuta.estado_proceso,
                                fecha_inicio_real: updatedItemRuta.fecha_inicio_real,
                                fecha_fin_real: updatedItemRuta.fecha_fin_real,
                                cantidad_terminado_proceso: updatedItemRuta.cantidad_terminado_proceso,
                                porcentaje_completado: updatedItemRuta.porcentaje_completado
                            }
                            : proceso
                    )
                }))
            );

            // Mostrar mensaje de éxito con iconos
            const estadoTexto = {
                'PENDIENTE': '🔵 Pendiente',
                'EN_PROCESO': '🟡 En Proceso',
                'COMPLETADO': '🟢 Completado',
                'PAUSADO': '🟠 Pausado',
                'CANCELADO': '🔴 Cancelado'
            };
            
            toast.success(`Estado actualizado a: ${estadoTexto[nuevoEstado]}`);

            // Sugerencias específicas según el estado
            if (nuevoEstado === 'EN_PROCESO') {
                setTimeout(() => {
                    toast('💡 Proceso iniciado. Registre el progreso usando el botón "📊 Progreso"', {
                        icon: '💡',
                        duration: 4000,
                        style: {
                            borderRadius: '10px',
                            background: '#e8f5e8',
                            color: '#2d5a2d',
                        },
                    });
                }, 1000);
            } else if (nuevoEstado === 'COMPLETADO') {
                toast('✅ ¡Proceso completado! Se actualizó automáticamente la cantidad terminada', {
                    icon: '✅',
                    duration: 3000,
                    style: {
                        background: '#d1f2eb',
                        color: '#0c5d56',
                    },
                });
            } else if (nuevoEstado === 'PAUSADO') {
                toast('⏸️ Proceso pausado. Podrá reanudarlo cambiando el estado a "En Proceso"', {
                    icon: '⏸️',
                    duration: 3000,
                    style: {
                        background: '#fff3cd',
                        color: '#856404',
                    },
                });
            }

        } catch (error) {
            console.error('Error actualizando estado:', error);
            
            // Mostrar error específico del backend si está disponible
            const errorMessage = error.response?.data?.error || error.message || 'Error desconocido';
            toast.error(`Error actualizando estado: ${errorMessage}`);
        }
    };

    const handleResetearAvance = async (itemRutaId) => {
        if (!window.confirm('¿Está seguro de resetear el avance de este proceso a 0?')) {
            return;
        }
        
        try {
            const response = await axios.patch(`/gestion/api/v1/item-ruta/${itemRutaId}/progress/`, {
                cantidad_completada: 0,
                observaciones: 'Avance reseteado desde programa'
            });
            
            if (response.data) {
                toast.success('Avance reseteado correctamente');
                await fetchProgramData(); // Recargar datos
            }
        } catch (error) {
            console.error('Error reseteando avance:', error);
            toast.error('Error al resetear el avance');
        }
    };

    const calcularResumenPlanificacion = () => {
        if (!programData?.ordenes_trabajo) return null;
        
        let totalProcesos = 0;
        let procesosCompletos = 0;
        let procesosConAvance = 0;
        let procesosPorPlanificar = 0;
        let unidadesTotales = 0;
        let unidadesCompletadas = 0;
        let unidadesRestantes = 0;
        
        programData.ordenes_trabajo.forEach(ot => {
            ot.procesos?.forEach(proceso => {
                totalProcesos++;
                const cantidadTotal = parseFloat(proceso.cantidad || 0);
                const cantidadTerminada = parseFloat(proceso.cantidad_terminado_proceso || 0);
                const cantidadRestante = Math.max(0, cantidadTotal - cantidadTerminada);
                const porcentaje = cantidadTotal > 0 ? (cantidadTerminada / cantidadTotal) * 100 : 0;
                
                unidadesTotales += cantidadTotal;
                unidadesCompletadas += cantidadTerminada;
                unidadesRestantes += cantidadRestante;
                
                if (porcentaje >= 100) {
                    procesosCompletos++;
                } else if (cantidadTerminada > 0) {
                    procesosConAvance++;
                }
                
                if (cantidadRestante > 0 && porcentaje < 100) {
                    procesosPorPlanificar++;
                }
            });
        });
        
        return {
            totalProcesos,
            procesosCompletos,
            procesosConAvance,
            procesosPorPlanificar,
            unidadesTotales,
            unidadesCompletadas,
            unidadesRestantes,
            porcentajeGeneral: unidadesTotales > 0 ? (unidadesCompletadas / unidadesTotales) * 100 : 0
        };
    };

    return (
        <div className="page-container">
            <CompNavbar />
            
            <div className="content-wrapper">
                <div className="container">
                    <div className="program-header">
                        <div className="d-flex justify-content-between align-items-center mb-4">
                            <div>
                                <Link to="/programs" className="btn btn-outline-primary">
                                    <FaArrowLeft className="me-2" />
                                    Volver a Programas
                                </Link>
                            </div>
                            <div className="text-center">
                                <h1 className="h3 mb-2">{programData?.nombre}</h1>
                                <div className="program-dates">
                                    <Badge bg="info" className="me-3">
                                        <FaCalendarAlt className="me-2" />
                                        Inicio: {programData?.fecha_inicio}
                                    </Badge>
                                    <Badge bg="info">
                                        <FaFlag className="me-2" />
                                        Término: {programData?.fecha_fin}
                                    </Badge>
                                </div>
                            </div>
                            <div className="action-buttons">
                                <Button 
                                    variant="outline-primary" 
                                    className="me-2"
                                    onClick={() => setShowAgregarOrden(true)}
                                >
                                    <FaPlus className="me-2" />
                                    Agregar Órdenes
                                </Button>
                                <Button 
                                    variant="outline-success" 
                                    className="me-2"
                                    onClick={() => generateProgramPDF(programId)}
                                >
                                    <FaFilePdf className="me-2" />
                                    PDF
                                </Button>
                                {/*<Button 
                                    variant="outline-info"
                                    onClick={() => navigate(`/programs/${programId}/supervisor-report`)}
                                >
                                    <FaClipboardList className="me-2" />
                                    Reporte
                                </Button>*/}

                                
                                {/*<Button 
                                    variant="warning" 
                                    onClick={verificarReajustes}
                                    className="ms-2"
                                >
                                    Verificar Disponibilidad
                                </Button>*/}
                            </div>
                            <ProgramHistory programId={programId} isAdmin={isAdmin} />
                        </div>
                    </div>
                    <ProgramMonitoring programId={programId}/>

                    {/* ✅ NUEVO PANEL DE RESUMEN DE PLANIFICACIÓN */}
                    {programData && (() => {
                        const resumen = calcularResumenPlanificacion();
                        if (!resumen) return null;
                        
                        return (
                            <Card className="mb-3 border-info">
                                <Card.Body className="py-3">
                                    <Row className="text-center">
                                        <Col md={2}>
                                            <div>
                                                <h5 className="text-primary mb-1">{resumen.procesosPorPlanificar}</h5>
                                                <small className="text-muted">Por planificar</small>
                                            </div>
                                        </Col>
                                        <Col md={2}>
                                            <div>
                                                <h5 className="text-success mb-1">{resumen.procesosCompletos}</h5>
                                                <small className="text-muted">Completados</small>
                                            </div>
                                        </Col>
                                        <Col md={2}>
                                            <div>
                                                <h5 className="text-warning mb-1">{otsConInconsistencias.length}</h5>
                                                <small className="text-muted">Con inconsistencias</small>
                                            </div>
                                        </Col>
                                        <Col md={3}>
                                            <div>
                                                <h5 className="text-info mb-1">{resumen.unidadesRestantes.toLocaleString()}</h5>
                                                <small className="text-muted">Unidades restantes</small>
                                            </div>
                                        </Col>
                                        <Col md={3}>
                                            <div>
                                                <h5 className="text-secondary mb-1">{resumen.porcentajeGeneral.toFixed(1)}%</h5>
                                                <small className="text-muted">Progreso general</small>
                                            </div>
                                        </Col>
                                    </Row>
                                    
                                    {/* ✅ ALERTAS IMPORTANTES */}
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
                        );
                    })()}

                    <section
                        className="container-section container-fluid border py-2 mb-2"
                        style={{ borderRadius: "5px" }}
                    >
                        <h2>Órdenes de Trabajo:</h2>
                        {hayProcesosConEstandarCero() && (
                            <AlertMessage
                                type="warning"
                                icon={<FaExclamationTriangle size={20} />}
                                message="Hay procesos con estándar en 0. Por favor, ingrese un valor válido para poder proyectar en la carta."
                            />
                        )}

                        {showPendingChangesAlert && Object.keys(pendingChanges).length > 0 && (
                            <div className="alert alert-info" role="alert">
                                <i className="bi bi-info-circle-fill me-2"></i>
                                Hay cambios pendientes por guardar. Por favor, guarde los cambios antes de salir de la página.
                            </div>
                        )}
                        
                        <div>
                            {otList && otList.length > 0 ? (
                                <ReactSortable
                                    list={otList}
                                    setList={setOtList}
                                    onEnd={(evt) => {
                                        const newOtList = [...otList];
                                        const movedItem = newOtList.splice(evt.oldIndex, 1)[0];
                                        newOtList.splice(evt.newIndex, 0, movedItem);
                                        handleOtReorder(newOtList);
                                    }}
                                >
                                    {otList.map((ot) => renderOt(ot))}
                                </ReactSortable>
                            ) : (
                                <p>No hay OTs asignadas a este programa.</p>
                            )}
                        </div>
                        <div className="d-flex align-items-center">
                            <Button 
                                variant="success" 
                                onClick={toggleTimeline} 
                                className="mt-3 me-2" 
                                disabled={timelineLoading || hayProcesosConEstandarCero()}
                                title={hayProcesosConEstandarCero() ? "No se puede proyectar: Hay procesos con estándar en 0" : ""}
                            >
                                {timelineLoading ? (
                                    <span>
                                        <LoadingSpinner message="" size="small"/> Cargando Proyección
                                    </span>
                                ) : showTimeline ? "Ocultar Proyección" : "Mostrar Proyección"}
                            </Button>

                            {/* NUEVO: Botón para Timeline Tiempo Real */}
                            <Button
                                variant="info"
                                onClick={() => setShowTimelineTimeReal(!showTimelineTimeReal)}
                                className="mt-3 me-2"
                            >
                                {showTimelineTimeReal ? "Ocultar Tiempo Real" : "Mostrar Tiempo Real"}
                            </Button>

                            {showTimeline && (
                                <div className="btn-group mt-3">
                                    <Button
                                        variant={timelineMode === 'planning' ? 'primary' : 'outline-primary'}
                                        onClick={() => setTimelineMode('planning')}
                                    >
                                        Planificación
                                    </Button>
                                    <Button
                                        variant={timelineMode === 'execution' ? 'primary' : 'outline-primary'}
                                        onClick={() => setTimelineMode('execution')}
                                    >
                                        Ejecución
                                    </Button>
                                </div>
                            )}
                        </div>
                    </section>

                    {/* NUEVO: Timeline Tiempo Real */}
                    {showTimelineTimeReal && (
                        <TimelineTimeReal 
                            programId={programId}
                            onTimelineUpdated={(timeline) => {
                                console.log('Timeline tiempo real actualizada:', timeline);
                            }}
                        />
                    )}

                    {/* Timeline existente */}
                    {showTimeline && (
                        <div className="timeline-container mt-4 mb-4" style={{ width: "100%" }}>
                            <Timeline
                                groups={timelineGroups}
                                items={timelineItems}
                                defaultTimeStart={moment('2025-07-01').startOf('day').toDate()}
                                defaultTimeEnd={moment('2025-07-15').endOf('day').toDate()}
                                lineHeight={50}
                                sidebarWidth={200}
                                canMove={false}
                                canResize={false}
                                stackItems
                                timeSteps={{
                                    second: 1,
                                    minute: 30,
                                    hour: 1,
                                    day: 1,
                                    month: 1,
                                    year: 1
                                }}
                                traditionalZoom
                                itemRenderer={({ item, itemContext, getItemProps }) => {
                                    

                                    // Verificar si falta alguna propiedad crítica
                                    if (!item.itemProps) {
                                            console.error('❌ ITEM SIN itemProps:', item);
                                            return <div>Error: Sin itemProps</div>;
                                        }
                                        return (
                                            <div
                                                {...getItemProps({
                                                    className: `${timelineMode === 'execution' ? 'execution-timeline-item' : ''}`,
                                                    style: {
                                                        ...item.itemProps.style,
                                                        borderRadius: '4px',
                                                        padding: '2px 6px'
                                                    }
                                                })}
                                                title={item.itemProps['data-tooltip']}
                                            >
                                                <div className="timeline-item-content">
                                                    <div className="item-title">{item.title}</div>
                                                    {timelineMode === 'execution' && item.porcentaje_avance !== undefined &&(
                                                        <div className="progress">
                                                            <div 
                                                                className="progress-bar" 
                                                                style={{ 
                                                                    width: `${item.porcentaje_avance || 0}%`
                                                                }}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    }}
                            />
                        </div>
                    )}


                </div>
            </div>
            <Footer />
            <AgregarOrdenModal 
                show={showAgregarOrden}
                onHide={() => setShowAgregarOrden(false)}
                programId={programId}
                onOrdenesAgregadas={handleOrdenesAgregadas}
            />
            <Modal show={showReajustesModal} onHide={() => setShowReajustesModal(false)} size="lg">
                <Modal.Header closeButton>
                    <Modal.Title>Ajustes Necesarios</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    {ajustes && (
                        <>
                            <Alert variant="info">
                                <strong>Fecha actual de fin:</strong> {ajustes.fecha_actual}<br/>
                                <strong>Nueva fecha de fin propuesta:</strong> {ajustes.nueva_fecha_fin}
                            </Alert>
                            
                            <div className="mb-3">
                                <strong>Total de ajustes necesarios: </strong> 
                                {ajustes.ajustes_sugeridos.length}
                            </div>
                            
                            {ajustes.ajustes_sugeridos.map((ajuste, index) => (
                                <Card key={`${ajuste.orden_trabajo}-${ajuste.proceso.id}`} className="mb-3">
                                    <Card.Header className="d-flex justify-content-between align-items-center">
                                        <span className="fw-bold">OT: {ajuste.orden_trabajo}</span>
                                        <Badge bg={index === 0 ? "warning" : "info"}>
                                            {index === 0 ? "Primer ajuste necesario" : `Ajuste #${index + 1}`}
                                        </Badge>
                                    </Card.Header>
                                    <Card.Body>
                                        <div className="row">
                                            <div className="col-md-6">
                                                <h6>Proceso</h6>
                                                <p>{ajuste.proceso.descripcion}</p>
                                                <h6>Máquina</h6>
                                                <p>
                                                    <strong>{ajuste.maquina.codigo}</strong> - {ajuste.maquina.descripcion}
                                                </p>
                                            </div>
                                            <div className="col-md-6">
                                                <h6>Fechas</h6>
                                                <div className="text-danger">
                                                    <small>Original: {new Date(ajuste.fecha_original).toLocaleString()}</small>
                                                </div>
                                                <div className="text-success">
                                                    <small>Propuesta: {new Date(ajuste.fecha_propuesta).toLocaleString()}</small>
                                                </div>
                                            </div>
                                        </div>
                                    </Card.Body>
                                </Card>
                            ))}
                        </>
                    )}
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => setShowReajustesModal(false)}>
                        Cancelar
                    </Button>
                    <Button 
                        variant="primary" 
                        onClick={aplicarReajustes}
                        disabled={!ajustes || ajustes.ajustes_sugeridos.length === 0}
                    >
                        Aplicar Ajustes
                    </Button>
                </Modal.Footer>
            </Modal>
            
            {/* NUEVO: Modal de progreso */}
            <ItemRutaProgressModal
                show={showProgressModal}
                onHide={() => setShowProgressModal(false)}
                itemRuta={selectedItemRuta}
                otData={selectedOtData}
                onProgressUpdated={handleProgressUpdated}
            />

            {/* ✅ NUEVO MODAL DE ANÁLISIS */}
            <AnalisisAvancesModal
                show={showAnalisisAvances}
                onHide={() => setShowAnalisisAvances(false)}
                programId={programId}
                otId={selectedOtAnalisis?.orden_trabajo}
                otData={selectedOtAnalisis}
                onAvancesActualizados={() => {
                    fetchProgramData();
                    cargarOTsConInconsistencias();
                }}
            />

            {/* Agregar botón en la interfaz: */}
            <button 
                onClick={() => setShowInconsistencias(true)}
                className="btn-inconsistencias"
            >
                🔍 Revisar Inconsistencias
            </button>

            {/* Agregar modal: */}
            <InconsistenciasModal 
                programaId={programId}
                isOpen={showInconsistencias}
                onClose={() => setShowInconsistencias(false)}
            />
        </div>
    );
}
