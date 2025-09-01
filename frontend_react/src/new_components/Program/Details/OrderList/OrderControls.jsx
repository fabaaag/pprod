import React from 'react';
import { Button, ButtonGroup } from 'react-bootstrap';
import { FaPlus, FaFilePdf, FaHistory, FaExclamationTriangle } from 'react-icons/fa';

export const OrderControls = ({
    onAddOrder, 
    onGeneratePDF,
    onShowHistory,
    onCheckAdjustments,
    onShowTimelineReal,
    hasInconsistencies,
    isAdmin
}) => {
  return (
    <div className="action-buttons d-flex gap-2 align-items-center">
        <Button variant='outline-primary' onClick={onAddOrder}>
            <FaPlus className="me-2" />
            Agregar OT
        </Button>
        
        <Button variant='outline-secondary' onClick={onGeneratePDF}>
            <FaFilePdf className="me-2" />
            Generar PDF
        </Button>

        <ButtonGroup>
                <Button 
                    variant="outline-info"
                    onClick={onShowHistory}
                >
                    <FaHistory className="me-2" />
                    Historial
                </Button>

                {isAdmin && (
                    <Button 
                        variant="outline-warning"
                        onClick={onCheckAdjustments}
                    >
                        <FaExclamationTriangle className="me-2" />
                        Verificar Ajustes
                    </Button>
                )}
            </ButtonGroup>
            {hasInconsistencies && (
                <Button variant="warning" onClick={() => onShowTimelineReal()} className='ms-2'>
                    <FaExclamationTriangle className="me-2" />
                    Ver Inconsistencias
                </Button>
            )}
    </div>
  );
};

