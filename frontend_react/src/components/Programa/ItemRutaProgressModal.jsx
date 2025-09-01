import React, { useState, useEffect } from 'react';
import { Modal, Form, Button, ProgressBar, Alert, InputGroup, Badge, Accordion } from 'react-bootstrap';
import { toast } from 'react-hot-toast';
import { updateItemRutaProgress } from '../../api/programs.api';

export function ItemRutaProgressModal({ 
  show, 
  onHide, 
  itemRuta, 
  otData,
  onProgressUpdated 
}) {
  const [formData, setFormData] = useState({
    cantidad_completada_nueva: 0,
    observaciones: '',
    operador_id: null,
    cantidad_perdida: ''
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (itemRuta) {
      setFormData({
        cantidad_completada_nueva: 0, // Siempre iniciamos en 0 para nueva producción
        observaciones: '',
        operador_id: itemRuta.operador_id || null,
        cantidad_perdida: ''
      });
    }
  }, [itemRuta]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!itemRuta) return;

    try {
      setLoading(true);
      
      // Llamar API para actualizar progreso del ItemRuta
      const result = await updateItemRutaProgress(itemRuta.id, {
        cantidad_completada: formData.cantidad_completada_nueva,
        observaciones: formData.observaciones,
        operador_id: formData.operador_id,
        cantidad_perdida: formData.cantidad_perdida
      });
      
      toast.success('Progreso actualizado correctamente');
      onProgressUpdated(result);
      onHide();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al actualizar progreso');
    } finally {
      setLoading(false);
    }
  };

  if (!itemRuta) return null;

  // Calcular progreso actual
  const cantidadTotal = parseFloat(itemRuta.cantidad || 0);
  const cantidadTerminada = parseFloat(itemRuta.cantidad_terminado_proceso || 0);
  const nuevaCantidadTotal = cantidadTerminada + parseFloat(formData.cantidad_completada_nueva || 0);
  const porcentajeActual = cantidadTotal > 0 ? (cantidadTerminada / cantidadTotal) * 100 : 0;
  const porcentajeNuevo = cantidadTotal > 0 ? (nuevaCantidadTotal / cantidadTotal) * 100 : 0;

  // Verificar si es el último proceso de la OT
  const esUltimoProceso = otData?.procesos && 
    itemRuta.item === Math.max(...otData.procesos.map(p => p.item));

  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>
          Progreso de Proceso - {itemRuta.descripcion}
        </Modal.Title>
      </Modal.Header>
      
      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          {/* Información del proceso */}
          <div className="row mb-3">
            <div className="col-md-6">
              <h6>OT: {otData?.orden_trabajo_codigo_ot}</h6>
              <p className="text-muted">
                Proceso {itemRuta.item}: {itemRuta.codigo_proceso} - {itemRuta.descripcion}
              </p>
              <p className="text-muted">
                Máquina: {itemRuta.maquina_descripcion}
              </p>
            </div>
            <div className="col-md-6">
              <h6>Cantidad Total: {cantidadTotal}</h6>
              <p className="text-muted">
                Terminado anteriormente: {cantidadTerminada}
              </p>
              <p className="text-muted">
                Pendiente: {cantidadTotal - cantidadTerminada}
              </p>
            </div>
          </div>

          {/* Progreso actual */}
          <div className="mb-3">
            <label className="form-label">Progreso Actual</label>
            <ProgressBar now={porcentajeActual} label={`${porcentajeActual.toFixed(1)}%`} />
            <small className="text-muted">
              {cantidadTerminada} de {cantidadTotal} unidades completadas
            </small>
          </div>

          {/* Progreso proyectado */}
          {formData.cantidad_completada_nueva > 0 && (
            <div className="mb-3">
              <label className="form-label">Progreso Proyectado</label>
              <ProgressBar 
                now={Math.min(porcentajeNuevo, 100)} 
                label={`${porcentajeNuevo.toFixed(1)}%`}
                variant={porcentajeNuevo >= 100 ? 'success' : 'info'}
              />
              <div className="d-flex justify-content-between mt-1">
                <small className="text-success">
                  +{formData.cantidad_completada_nueva} unidades = {nuevaCantidadTotal} total
                </small>
                {porcentajeNuevo > 100 && (
                  <small className="text-warning">
                    🎯 Exceso: {(porcentajeNuevo - 100).toFixed(1)}%
                  </small>
                )}
              </div>
            </div>
          )}

          {/* Campo de cantidad producida HOY */}
          <div className="mb-3">
            <label className="form-label">
              <strong>Cantidad Producida en Esta Sesión</strong>
            </label>
            
            {/* Mostrar contexto de cantidad ya finalizada */}
            {cantidadTerminada > 0 && (
              <Alert variant="info" className="mb-2">
                <div className="row">
                  <div className="col-6">
                    <small><strong>Ya completado:</strong> {cantidadTerminada} unidades</small>
                  </div>
                  <div className="col-6">
                    <small><strong>Pendiente:</strong> {cantidadTotal - cantidadTerminada} unidades</small>
                  </div>
                </div>
                <hr className="my-2" />
                <small className="text-muted">
                  ℹ️ Ingrese solo la cantidad <strong>nueva</strong> producida en esta sesión
                </small>
              </Alert>
            )}
            
            <InputGroup>
              <InputGroup.Text>➕</InputGroup.Text>
              <Form.Control
                type="number"
                step="1"
                min="0"
                value={formData.cantidad_completada_nueva}
                onChange={(e) => setFormData({
                  ...formData,
                  cantidad_completada_nueva: parseInt(e.target.value) || 0
                })}
                required
                placeholder="Unidades adicionales producidas ahora"
              />
              <InputGroup.Text>unidades</InputGroup.Text>
            </InputGroup>
            
            <Form.Text className="text-muted">
              Solo ingrese la cantidad <strong>nueva</strong> producida. 
              Total después: {nuevaCantidadTotal} unidades
            </Form.Text>

            {/* Mostrar cálculo visual del resultado */}
            {formData.cantidad_completada_nueva > 0 && (
              <div className="mt-2 p-2 bg-light rounded">
                <small>
                  <strong>Cálculo:</strong> {cantidadTerminada} (anterior) + {formData.cantidad_completada_nueva} (nueva) = {nuevaCantidadTotal} (total)
                </small>
              </div>
            )}

            {formData.cantidad_completada_nueva > (cantidadTotal - cantidadTerminada) && (
              <Alert variant="warning" className="mt-2">
                <small>
                  ⚠️ <strong>Sobreproducción detectada:</strong> 
                  {' '}+{formData.cantidad_completada_nueva - (cantidadTotal - cantidadTerminada)} unidades extras
                  <br />
                  <em>Esto puede ser intencional para compensar pérdidas futuras.</em>
                </small>
              </Alert>
            )}
          </div>
          

          {/* Observaciones */}
          <div className="mb-3">
            <label className="form-label">Observaciones</label>
            <Form.Control
              as="textarea"
              rows={2}
              value={formData.observaciones}
              onChange={(e) => setFormData({
                ...formData,
                observaciones: e.target.value
              })}
              placeholder="Comentarios sobre la producción..."
            />
          </div>

          {/* Sección de Fechas Reales */}
          <div className="mb-3">
            <label className="form-label"><strong>Fechas de Ejecución</strong></label>
            <div className="row">
              <div className="col-6">
                <small>Inicio Real: {itemRuta.fecha_inicio_real || 'No iniciado'}</small>
              </div>
              <div className="col-6">
                <small>Fin Real: {itemRuta.fecha_fin_real || 'En proceso'}</small>
              </div>
            </div>
          </div>

          {/* Sección de Calidad */}
          <div className="mb-3">
            <label className="form-label"><strong>Control de Calidad</strong></label>
            <InputGroup>
              <Form.Control
                type="number"
                placeholder="Cantidad perdida/rechazada"
                value={formData.cantidad_perdida}
                onChange={(e) => setFormData({...formData, cantidad_perdida: e.target.value})}
              />
            </InputGroup>
          </div>

          {/* Historial de Cambios */}
          {itemRuta.historial_progreso?.length > 0 && (
            <Accordion className="mb-3">
              <Accordion.Item eventKey="0">
                <Accordion.Header>📊 Historial de Progreso</Accordion.Header>
                <Accordion.Body>
                  {itemRuta.historial_progreso.slice(-5).map((cambio, idx) => (
                    <div key={idx} className="border-bottom pb-2 mb-2">
                      <small className="text-muted">{cambio.fecha}</small>
                      <div>{cambio.tipo}: {JSON.stringify(cambio.datos)}</div>
                    </div>
                  ))}
                </Accordion.Body>
              </Accordion.Item>
            </Accordion>
          )}

          {/* Alertas especiales */}
          {porcentajeNuevo >= 100 && porcentajeNuevo <= 110 && (
            <Alert variant="success">
              <strong>🎉 ¡Proceso Completado!</strong> 
              {porcentajeNuevo > 100 && (
                <span> Con {(porcentajeNuevo - 100).toFixed(1)}% de sobreproducción.</span>
              )}
            </Alert>
          )}

          {porcentajeNuevo > 110 && (
            <Alert variant="warning">
              <strong>📊 Sobreproducción Significativa</strong> 
              <br />
              Se está produciendo {(porcentajeNuevo - 100).toFixed(1)}% más de lo planificado.
              <br />
              <small>Verifique si esto es intencional y agregue observaciones.</small>
            </Alert>
          )}

          {esUltimoProceso && porcentajeNuevo >= 100 && (
            <Alert variant="info">
              <strong>📋 Último Proceso</strong> Al completar este proceso, 
              se actualizará el avance general de la OT {otData?.orden_trabajo_codigo_ot}.
              {porcentajeNuevo > 100 && (
                <><br /><small>⚠️ La sobreproducción se reflejará en el avance de la OT.</small></>
              )}
            </Alert>
          )}

          {/* Estado actual del operador */}
          {itemRuta.operador_nombre && (
            <div className="mb-2">
              <Badge bg="info">
                Operador asignado: {itemRuta.operador_nombre}
              </Badge>
            </div>
          )}
        </Modal.Body>

        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={loading}>
            Cancelar
          </Button>
          <Button 
            type="submit" 
            variant="primary" 
            disabled={loading || formData.cantidad_completada_nueva <= 0}
          >
            {loading ? 'Actualizando...' : 'Registrar Progreso'}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}