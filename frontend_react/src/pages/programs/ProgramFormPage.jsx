import { useForm } from "react-hook-form";
import { createProgram } from "../../api/programs.api";
import axios from '../../api/axiosConfig';
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import CompNavbar from "../../components/Navbar/CompNavbar";
import { Card, Form, Button, Badge, InputGroup } from 'react-bootstrap';
import { FaSearch, FaCalendarAlt, FaClipboardList, FaArrowLeft, FaFilter } from 'react-icons/fa';
import './ProgramForm.css';

export function ProgramFormPage() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const navigate = useNavigate();
  const [unassignedOrders, setUnassignedOrders] = useState([]);
  const [selectedOrders, setSelectedOrders] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterAvance, setFilterAvance] = useState("all");
  const [loading, setLoading] = useState(false);

  const fetchUnassignedOrders = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/gestion/api/v1/ordenes/no_asignadas/");
      setUnassignedOrders(response.data);
    } catch (error) {
      toast.error("Error al cargar las órdenes");
    } finally {
      setLoading(false);
    }
  };

  const handleOrderSelection = (order) => {
    if (selectedOrders.some((selected) => selected.id === order.id)) {
      setSelectedOrders(selectedOrders.filter((selected) => selected.id !== order.id));
    } else {
      setSelectedOrders([...selectedOrders, order]);
    }
  };

  const filteredOrders = unassignedOrders.filter(order => {
    const matchesSearch = 
      order.codigo_ot.toString().includes(searchTerm) ||
      order.descripcion_producto_ot.toLowerCase().includes(searchTerm.toLowerCase());

    // Filtro de avances
    const cantidad_avance = parseFloat(order.cantidad_avance) || 0;
    let matchesAvance = true;
    
    switch(filterAvance) {
      case 'nuevas':
        matchesAvance = cantidad_avance === 0;
        break;
      case 'historicas':
        matchesAvance = cantidad_avance > 0;
        break;
      case 'all':
      default:
        matchesAvance = true;
        break;
    }

    return matchesSearch && matchesAvance;
  });

  const getAvanceInfo = (order) => {
    const cantidad_avance = parseFloat(order.cantidad_avance) || 0;
    const cantidad_total = parseFloat(order.cantidad) || 0;
    const porcentaje = cantidad_total > 0 ? (cantidad_avance / cantidad_total) * 100 : 0;
    
    if (cantidad_avance === 0) {
      return { 
        color: 'success', 
        text: 'Nueva', 
        porcentaje: 0,
        description: 'Sin avance previo'
      };
    } else if (porcentaje >= 100) {
      return { 
        color: 'warning', 
        text: 'Completa', 
        porcentaje: porcentaje,
        description: `${cantidad_avance}/${cantidad_total} - Completa`
      };
    } else {
      return { 
        color: 'info', 
        text: `${porcentaje.toFixed(1)}%`, 
        porcentaje: porcentaje,
        description: `${cantidad_avance}/${cantidad_total} - En progreso`
      };
    }
  };

  const onSubmit = handleSubmit(async (data) => {
    try {
      setLoading(true);
      const programData = {
        ...data,
        ordenes: selectedOrders.map((order) => order.id),
      };
      
      const response = await createProgram(programData);
      if(response.status === 201) {
        toast.success("Programa creado exitosamente");
        navigate("/programs");
      }
    } catch (error) {
      toast.error("Error al crear el programa");
    } finally {
      setLoading(false);
    }
  });

  useEffect(() => {
    fetchUnassignedOrders();
  }, []);

  return (
    <div className="bg-light min-vh-100">
      <CompNavbar />
      <div className="container py-4">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <div>
            <h1 className="h3 mb-0">Crear Programa de Producción</h1>
            <p className="text-muted">Complete los detalles del nuevo programa</p>
          </div>
          <Button 
            variant="outline-secondary" 
            onClick={() => navigate('/programs')}
            className="d-flex align-items-center gap-2"
          >
            <FaArrowLeft /> Volver
          </Button>
        </div>

        <div className="row">
          {/* Formulario Principal */}
          <div className="col-md-4">
            <Card className="shadow-sm mb-4">
              <Card.Body>
                <Form onSubmit={onSubmit}>
                  <Form.Group className="mb-3">
                    <Form.Label>Nombre del Programa</Form.Label>
                    <Form.Control
                      type="text"
                      {...register("nombre", { required: "El nombre es requerido" })}
                      isInvalid={!!errors.nombre}
                    />
                    <Form.Control.Feedback type="invalid">
                      {errors.nombre?.message}
                    </Form.Control.Feedback>
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>
                      <FaCalendarAlt className="me-2" />
                      Fecha de Inicio
                    </Form.Label>
                    <Form.Control
                      type="date"
                      {...register("fecha_inicio", { required: "La fecha de inicio es requerida" })}
                      isInvalid={!!errors.fecha_inicio}
                    />
                    <Form.Control.Feedback type="invalid">
                      {errors.fecha_inicio?.message}
                    </Form.Control.Feedback>
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label>
                      <FaCalendarAlt className="me-2" />
                      Fecha de Término
                    </Form.Label>
                    <Form.Control
                      type="date"
                      {...register("fecha_termino", { required: "La fecha de término es requerida" })}
                      isInvalid={!!errors.fecha_termino}
                    />
                    <Form.Control.Feedback type="invalid">
                      {errors.fecha_termino?.message}
                    </Form.Control.Feedback>
                  </Form.Group>

                  <Button 
                    type="submit" 
                    variant="primary" 
                    className="w-100"
                    disabled={loading || selectedOrders.length === 0}
                  >
                    {loading ? 'Creando...' : 'Crear Programa'}
                  </Button>
                </Form>
              </Card.Body>
            </Card>

            {selectedOrders.length > 0 && (
              <Card className="shadow-sm">
                <Card.Body>
                  <h6 className="mb-3">Resumen de Selección</h6>
                  <div className="small">
                    <div className="d-flex justify-content-between mb-2">
                      <span>Total órdenes:</span>
                      <Badge bg="primary">{selectedOrders.length}</Badge>
                    </div>
                    <div className="d-flex justify-content-between mb-2">
                      <span>OTs nuevas:</span>
                      <Badge bg="success">
                        {selectedOrders.filter(o => (parseFloat(o.cantidad_avance) || 0) === 0).length}
                      </Badge>
                    </div>
                    <div className="d-flex justify-content-between">
                      <span>OTs con historial:</span>
                      <Badge bg="info">
                        {selectedOrders.filter(o => (parseFloat(o.cantidad_avance) || 0) > 0).length}
                      </Badge>
                    </div>
                  </div>
                </Card.Body>
              </Card>
            )}
          </div>

          {/* Selección de Órdenes */}
          <div className="col-md-8">
            <Card className="shadow-sm">
              <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="mb-0">
                    <FaClipboardList className="me-2" />
                    Órdenes de Trabajo
                  </h5>
                  <Badge bg="primary">
                    {selectedOrders.length} órdenes seleccionadas
                  </Badge>
                </div>

                <div className="row g-3 mb-3">
                  <div className="col-md-6">
                    <InputGroup>
                      <InputGroup.Text>
                        <FaSearch />
                      </InputGroup.Text>
                      <Form.Control
                        placeholder="Buscar órdenes..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </InputGroup>
                  </div>
                  <div className="col-md-4">
                    <Form.Select
                      value={filterAvance}
                      onChange={(e) => setFilterAvance(e.target.value)}
                    >
                      <option value="all">Todas las órdenes</option>
                      <option value="nuevas">🆕 OTs nuevas</option>
                      <option value="historicas">📊 Con historial</option>
                    </Form.Select>
                  </div>
                  <div className="col-md-2">
                    <div className="d-flex align-items-center h-100">
                      <small className="text-muted">
                        <FaFilter className="me-1" />
                        {filteredOrders.length} OTs
                      </small>
                    </div>
                  </div>
                </div>

                <div className="orders-grid">
                  {filteredOrders.map((order) => {
                    const avanceInfo = getAvanceInfo(order);
                    
                    return (
                      <Card 
                        key={order.id}
                        className={`order-card ${
                          selectedOrders.some(selected => selected.id === order.id) ? 'selected' : ''
                        }`}
                        onClick={() => handleOrderSelection(order)}
                      >
                        <Card.Body>
                          <div className="d-flex justify-content-between align-items-start mb-2">
                            <div className="flex-grow-1">
                              <h6 className="mb-1">OT #{order.codigo_ot}</h6>
                              <p className="text-muted small mb-0">{order.descripcion_producto_ot}</p>
                            </div>
                            <Form.Check
                              type="checkbox"
                              checked={selectedOrders.some(selected => selected.id === order.id)}
                              onChange={() => {}}
                              className="mt-1"
                            />
                          </div>
                          
                          <div className="d-flex justify-content-between align-items-center">
                            <Badge bg={avanceInfo.color} className="me-2">
                              {avanceInfo.text}
                            </Badge>
                            <small className="text-muted">
                              {avanceInfo.description}
                            </small>
                          </div>
                          
                          {avanceInfo.porcentaje > 0 && (
                            <div className="progress mt-2" style={{height: "4px"}}>
                              <div 
                                className="progress-bar" 
                                role="progressbar"
                                style={{
                                  width: `${avanceInfo.porcentaje}%`
                                }}
                              />
                            </div>
                          )}
                        </Card.Body>
                      </Card>
                    );
                  })}
                </div>
              </Card.Body>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProgramFormPage;
