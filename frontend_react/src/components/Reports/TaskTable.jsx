import React, { useState } from 'react';
import { Table, Form, Button } from 'react-bootstrap';
import { FaUserPlus, FaSave } from 'react-icons/fa';
import './css/TaskTable.css';

export const TaskTable = ({ 
    tasks, 
    onTasksUpdate,
    onOperatorAssign,
    kilosFabricados,
    onKilosChange,
    taskStates,
    onStateChange,
    onObservacionesChange,
    onSaveTask,
    unidadesFabricadas
}) => {
    // Estado para controlar qué filas han sido modificadas
    const [modifiedRows, setModifiedRows] = useState({});

    // Primero añadimos un estado para manejar las alertas
    const [alerts, setAlerts] = useState({});

    // Función auxiliar para marcar una fila como modificada
    const markAsModified = (taskId) => {
        setModifiedRows(prev => ({
            ...prev,
            [taskId]: true
        }));
    };

    // Función para guardar todos los cambios pendientes
    const handleSaveAllChanges = () => {
        // Obtener todos los IDs de tareas modificadas
        const modifiedTaskIds = Object.keys(modifiedRows).filter(id => modifiedRows[id]);
        
        // Para cada tarea modificada, llamar a onSaveTask
        modifiedTaskIds.forEach(taskId => {
            const task = tasks.find(t => t.id.toString() === taskId);
            if (task) {
                onSaveTask(taskId, task);
            }
        });
        
        // Limpiar todas las modificaciones
        setModifiedRows({});
    };

    // Manejadores locales
    const handleKilosChange = (taskId, value, task) => {
        // Convertir el valor a número
        const kilos = parseFloat(value) || 0;
        const kilosProgramados = parseFloat(task.kilos.programados) || 0;
        
        // Notificar solo cuando se alcance el 100% pero permitir continuar
        if (kilos > 0 && kilosProgramados > 0) {
            const porcentajeCompletado = (kilos / kilosProgramados) * 100;
            
            if (porcentajeCompletado >= 100) {
                // Solo mostrar confirmación para marcar como completado
                const confirmar = window.confirm('Se alcanzó el 100% de los kilos programados. ¿Desea marcar la tarea como COMPLETADA?');
                if (confirmar) {
                    handleStateChange(taskId, 'COMPLETADO', task);
                }
            }
        }
        
        // Actualizar el estado de kilos y marcar como modificado
        onKilosChange(taskId, kilos, task);
        markAsModified(taskId);
        
        // Calcular unidades basado en peso unitario sin limitación
        if (task.orden_trabajo && task.orden_trabajo.peso_unitario) {
            const pesoUnitario = parseFloat(task.orden_trabajo.peso_unitario);
            if (pesoUnitario > 0) {
                const unidades = Math.round(kilos / pesoUnitario);
                
                // Calcular el porcentaje sin limitar al 100%
                const cantidadReferencia = task.es_continuacion ? 
                    task.cantidades.programada : 
                    task.cantidades.total_dia;
                
                const porcentajeCumplimiento = cantidadReferencia > 0 ? 
                    (unidades / cantidadReferencia) * 100 : 0;
                
                // Actualizar la tarea con las unidades y el nuevo porcentaje
                const updatedTasks = tasks.map(t => 
                    t.id === taskId 
                        ? { 
                            ...t, 
                            cantidades: {
                                ...t.cantidades,
                                completada: unidades
                            },
                            porcentaje_cumplimiento: porcentajeCumplimiento
                        } 
                        : t
                );
                onTasksUpdate(updatedTasks);
            }
        }
    };

    const handleStateChange = (taskId, value, task) => {
        onStateChange(taskId, value, task);
        markAsModified(taskId);
    };

    const handleObservacionesChange = (taskId, value, task) => {
        onObservacionesChange(taskId, value, task);
        markAsModified(taskId);
    };

    // Verificar si hay cambios pendientes
    const hasPendingChanges = Object.values(modifiedRows).some(modified => modified);

    const renderTaskRow = (task, index) => (
        <tr key={task.id} className={modifiedRows[task.id] ? 'row-modified' : (task.es_continuacion ? 'tarea-continuacion' : '')}>
            <td className="text-center">{index + 1}</td>
            <td>{task.orden_trabajo.codigo}</td>
            <td>
                <div>
                    {task.proceso.descripcion}
                    {task.es_continuacion && (
                        <span className="badge bg-info ms-2">
                            Continuación
                        </span>
                    )}
                </div>
                <small className="text-muted">
                    {task.proceso.codigo}
                </small>
            </td>
            <td>
                <div>{task.maquina?.descripcion || 'Sin máquina'}</div>
                <small className="text-muted">
                    {task.maquina?.codigo || ''}
                </small>
            </td>
            <td>
                <div className="d-flex align-items-center justify-content-between">
                    <span>{task.operador?.nombre || 'Sin asignar'}</span>
                    <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => onOperatorAssign(task)}
                    >
                        <FaUserPlus />
                    </Button>
                </div>
            </td>
            <td className="text-end">
                <div>{task.cantidades.programada}</div>
                {task.cantidades.pendiente_anterior > 0 && (
                    <small className="text-muted">
                        +{task.cantidades.pendiente_anterior} pendiente
                    </small>
                )}
            </td>
            <td className="text-end">
                <div>
                    {unidadesFabricadas && unidadesFabricadas[task.id] !== undefined 
                        ? unidadesFabricadas[task.id] 
                        : task.cantidades.completada}
                </div>
                <small className="text-muted">
                    de {task.cantidades.total_dia}
                </small>
            </td>
            <td className="text-end">
                <div>{task.kilos.programados?.toFixed(2) || '0.00'}</div>
                <small className="text-muted">programados</small>
            </td>
            <td className="text-end">
                <div className="position-relative">
                    <Form.Control 
                        type="number"
                        step="0.01"
                        size="sm"
                        value={kilosFabricados[task.id] !== undefined ? kilosFabricados[task.id] : (task.kilos.fabricados ?? '')}
                        onChange={(e) => handleKilosChange(task.id, e.target.value, task)}
                        disabled={taskStates[task.id] === 'COMPLETADO'}
                        className={alerts[task.id]?.type === 'warning' ? 'border-warning' : ''}
                    />
                    <small className="text-muted d-block">fabricados</small>
                    {alerts[task.id] && (
                        <div className={`alert alert-${alerts[task.id].type} alert-sm mt-1 p-1`} 
                             style={{fontSize: '0.8rem'}}>
                            {alerts[task.id].message}
                        </div>
                    )}
                </div>
            </td>
            <td>
                <Form.Select
                    size="sm"
                    value={taskStates[task.id] || task.estado}
                    onChange={(e) => handleStateChange(task.id, e.target.value, task)}
                    className={`estado-${(taskStates[task.id] || task.estado).toLowerCase()}`}
                >
                    <option value="PENDIENTE">Pendiente</option>
                    <option value="EN_PROCESO">En Proceso</option>
                    <option value="COMPLETADO">Terminado</option>
                    <option value="DETENIDO">Detenido</option>
                </Form.Select>
            </td>
            <td className="text-center">
                <div className="progress-container">
                    <div className="progress" style={{ height: '20px' }}>
                        <div 
                            className={`progress-bar ${
                                task.porcentaje_cumplimiento >= 100 
                                    ? 'bg-success' 
                                    : task.porcentaje_cumplimiento > 0 
                                        ? 'bg-primary' 
                                        : 'bg-secondary'
                            }`}
                            role="progressbar"
                            style={{ 
                                width: `${Math.min(
                                    task.es_continuacion 
                                        ? (task.cantidades.completada / task.cantidades.programada * 100)
                                        : task.porcentaje_cumplimiento, 
                                    100
                                )}%` 
                            }}
                        >
                            {task.es_continuacion 
                                ? ((task.cantidades.completada / task.cantidades.programada * 100) || 0).toFixed(1)
                                : (task.porcentaje_cumplimiento || 0).toFixed(1)
                            }%
                        </div>
                    </div>
                </div>
            </td>
            <td>
                <Form.Control 
                    as="textarea"
                    rows={1}
                    size="sm"
                    value={task.observaciones || ''}
                    onChange={(e) => handleObservacionesChange(task.id, e.target.value, task)}
                    placeholder="Agregar observación"
                />
            </td>
        </tr>
    );

    return (
        <div className="task-table-container">
            {hasPendingChanges && (
                <div className="save-all-container mb-2 d-flex justify-content-end">
                    <Button
                        variant="success"
                        onClick={handleSaveAllChanges}
                        className="d-flex align-items-center"
                    >
                        <FaSave className="me-2" /> Guardar todos los cambios
                    </Button>
                </div>
            )}
            <Table striped bordered hover responsive className="table-expanded">
                <thead>
                    <tr>
                        <th className="text-center" style={{width: '3%'}}>Orden</th>
                        <th style={{width: '6%'}}>OT</th>
                        <th style={{width: '13%'}}>Proceso</th>
                        <th style={{width: '12%'}}>Máquina</th>
                        <th style={{width: '13%'}}>Operador</th>
                        <th className='text-end' style={{width: '7%'}}>Unid. Prog.</th>
                        <th className='text-end' style={{width: '7%'}}>Unid. Comp.</th>
                        <th className='text-end' style={{width: '6%'}}>Kg. Prog.</th>
                        <th className='text-end' style={{width: '10%'}}>Kg. Fab.</th>
                        <th style={{width: '9%'}}>Estado</th>
                        <th style={{width: '8%'}}>Avance</th>
                        <th style={{width: '20%'}}>Obs.</th>
                    </tr>
                </thead>
                <tbody>
                    {tasks.length > 0 ? (
                        tasks.map((task, index) => renderTaskRow(task, index))
                    ) : (
                        <tr>
                            <td colSpan="12" className="text-center py-3">
                                No hay tareas programadas para este día
                            </td>
                        </tr>
                    )}
                </tbody>
            </Table>
        </div>
    );
};

// Añadir estilos CSS necesarios
const styles = `
.alert-sm {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    margin: 0;
    position: absolute;
    z-index: 1000;
    width: max-content;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.position-relative {
    position: relative;
}
`;

// Agregar los estilos al documento
const styleSheet = document.createElement("style");
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);