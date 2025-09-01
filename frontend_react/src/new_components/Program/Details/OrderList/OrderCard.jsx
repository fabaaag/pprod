import React, { useState } from 'react';
import { Card, Badge, Button, Collapse } from 'react-bootstrap';
import { FaCalendarAlt, FaChevronDown } from 'react-icons/fa';

export const OrderCard = ({
    ot,
    isExpanded,
    onToggleExpand,
    onSaveChanges,
    savingChanges,
    children,
    tieneAvanceHistorico,
    tieneInconsistencias,
    otInconsistencias,
    maquinasPrincipales
}) => {
    const [showColorPicker, setShowColorPicker] = useState(false);
    

  return (
    <Card className="mb-3 order-card">
        <Card.Body>
            <div className="d-flex justify-content-between align-items-start">
                <div className="order-header">
                    <h6 className="mb-0">#{ot.orden_trabajo_codigo_ot}</h6>
                    <div className="d-flex gap-1 mt-1">
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
                        {maquinasPrincipales && maquinasPrincipales.length > 0  && (
                            <small className="text-info">
                                🏭{maquinasPrincipales.join(', ')}
                            </small>
                        )}
                    </div>
                </div>
                {/*
                <div className="ms-3 position-relative">
                    <Button 
                        className="btn btn-sm"
                        style={{
                            backgroundColor: ot.color || "#2196f3",
                            
                            border: "2px solid #fff",
                            borderRadius: "50%"
                        }}
                        onClick={() => setShowColorPicker(!showColorPicker)}
                    />

                    
                    {showColorPicker && (
                        <div className="position-absolute" >
                            <div className="position-fixed ">
                                
                            </div>
                        </div>
                    )}
                    </div>
                **/}
                <div className="d-flex gap-2">
                    {savingChanges !== undefined && (
                        <Button
                            variant='success'
                            size='sm'
                            onClick={onSaveChanges}
                            disabled={savingChanges}
                        >
                            {savingChanges ?  "Guardando..." : "Guardar"}
                        </Button>
                    )}
                    <Button
                        variant={isExpanded ? "primary" : "outline-primary"}
                        size="sm"
                        onClick={onToggleExpand}
                    >
                        <FaChevronDown 
                            className={`transition-transform ${
                                isExpanded ? 'rotate-180' : ''
                            }`}
                        />
                    </Button>
                </div>
            </div>
            <Collapse in={isExpanded}>
                <div>
                    {children}
                </div>
            </Collapse>
        </Card.Body>
    </Card>
  );
};

