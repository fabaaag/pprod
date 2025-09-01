import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, ListGroup } from 'react-bootstrap';
import { toast } from 'react-hot-toast';
// ✅ CORRECCIÓN: Importar las funciones que SÍ existen
import { getUnassignedOrders, addOrdersToProgram } from '../../../../api/programs.api';
import { LoadingSpinner } from '../../../../components/UI/LoadingSpinner/LoadingSpinner';

export const AddOrderModal = ({
    show,
    onHide,
    programId,
    onOrdenesAgregadas
}) => {
  const [availableOrders, setAvailableOrders] = useState([]);
  const [selectedOrders, setSelectedOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (show) {
        loadAvailableOrders();
    }
  }, [show]);

  const loadAvailableOrders = async () => {
    try {
        setLoading(true);
        // ✅ CORRECCIÓN: Usar getUnassignedOrders en lugar de getAvailableOrders
        const response = await getUnassignedOrders();
        console.log("ots dispo: ", response)
        setAvailableOrders(response.data || response);
    } catch (error) {
        console.error('Error cargando órdenes disponibles:', error);
        toast.error('Error al cargar órdenes disponibles');
    } finally {
        setLoading(false);
    }
  };

  const handleOrderSelect = (orderId) => {
    setSelectedOrders(prev => {
        if (prev.includes(orderId)) {
            return prev.filter(id => id !== orderId);
        }
        return [...prev, orderId];
    });
  };

  const handleSubmit = async () => {
    if (selectedOrders.length === 0){
        toast.error('Seleccione al menos una orden');
        return;
    }

    try {
        setLoading(true);
        // ✅ CORRECCIÓN: Usar addOrdersToProgram en lugar de addOrderToProgram
        await addOrdersToProgram(programId, selectedOrders);
        toast.success('Órdenes agregadas correctamente');
        onOrdenesAgregadas?.();
        onHide();
        setSelectedOrders([]); // Limpiar selección
    } catch (error) {
        console.error('Error agregando órdenes:', error);
        toast.error('Error al agregar órdenes');
    } finally {
        setLoading(false);
    }
  };

   const filteredOrders = availableOrders

   return (
        <Modal show={show} onHide={onHide} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Agregar Órdenes de Trabajo</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form.Group className="mb-3">
                    <Form.Control 
                        type="text"
                        placeholder="Buscar por código o descripción..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </Form.Group>

                {loading ? (
                    <LoadingSpinner message='Cargando órdenes...'/>
                ) : (
                    <>
                        {filteredOrders.length === 0 ? (
                            <Alert variant="info">
                                No hay órdenes disponibles para agregar
                            </Alert>
                        ) : (
                            <ListGroup
                                style={{ maxHeight: '50vh', overflowY: 'auto' }}
                            >
                                {filteredOrders.map(order => (
                                    <ListGroup.Item
                                        key={order.id}
                                        action
                                        active={selectedOrders.includes(order.id)}
                                        onClick={() => handleOrderSelect(order.id)}
                                        className='d-flex justify-content-between align-items-center'
                                    >
                                        <div>
                                            <strong>{order.codigo_ot}</strong>
                                            <p className="mb-0 text-muted">
                                                {order.descripcion_producto_ot}
                                            </p>
                                            <small>
                                                Cantidad: {order.cantidad}
                                            </small>
                                        </div>
                                        {selectedOrders.includes(order.id) && (
                                            <span className="badge bg-primary">✓ Seleccionada</span>
                                        )}
                                    </ListGroup.Item>
                                ))}
                            </ListGroup>
                        )}
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <div className="d-flex justify-content-between align-items-center w-100">
                    <small className="text-muted">
                        {selectedOrders.length > 0 && `${selectedOrders.length} orden(es) seleccionada(s)`}
                    </small>
                    <div>
                        <Button variant="secondary" onClick={onHide} className="me-2">
                            Cancelar
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleSubmit}
                            disabled={loading || selectedOrders.length === 0}
                        >
                            {loading ? 'Agregando...' : 
                             selectedOrders.length === 1 ? 'Agregar Orden' : 
                             `Agregar ${selectedOrders.length} Órdenes`}
                        </Button>
                    </div>
                </div>
            </Modal.Footer>
        </Modal>
   );
};
