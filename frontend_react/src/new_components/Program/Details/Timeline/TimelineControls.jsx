import React from 'react';
import { Button, ButtonGroup, Dropdown } from 'react-bootstrap';
import { FaProjectDiagram, FaCalendarAlt, FaChartLine } from 'react-icons/fa';

export const TimelineControls = ({
    showTimeline,
    timelineMode,
    timelineLoading,
    onToggleTimeline,
    onModeChange,
    hasProcessesWithZeroStandard,
    disabled
}) => {
    return (
        <div className="d-flex align-items-center gap-2 mb-3">
            <Button
                variant={showTimeline ? "primary" : "outline-primary"}
                onClick={onToggleTimeline}
                disabled={disabled || timelineLoading || hasProcessesWithZeroStandard}
                className="d-flex align-items-center"
            >
                <FaProjectDiagram className="me-2" />
                {showTimeline ? "Ocultar Timeline" : "Mostrar Timeline"}
            </Button>
            
            {showTimeline && (
                <ButtonGroup>
                    <Button
                        variant={timelineMode === 'planning' ? "info" : "outline-info"}
                        onClick={() => onModeChange('planning')}
                        disabled={timelineLoading || timelineMode === 'planning'}
                    >
                        <FaCalendarAlt className="me-2" />
                        Planificación
                    </Button>
                    <Button
                        variant={timelineMode === 'execution' ? "info" : "outline-info"}
                        onClick={() => onModeChange('execution')}
                        disabled={timelineLoading || timelineMode === 'execution'}
                    >
                        <FaChartLine className="me-2" />
                        Ejecución
                    </Button>
                </ButtonGroup>
            )}
            
            {timelineLoading && (
                <span className="ms-2 text-muted">
                    Cargando datos...
                </span>
            )}
            
            {hasProcessesWithZeroStandard && !showTimeline && (
                <span className="ms-2 text-danger">
                    ⚠️ Hay procesos con estándar en 0
                </span>
            )}
        </div>
    );
};

