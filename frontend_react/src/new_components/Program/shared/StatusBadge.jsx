import React from 'react';
import { Badge } from 'react-bootstrap';

const getStatusColor = (status) => {
    switch(status){
        case 'COMPLETADO':
            return 'success';
        case 'EN_PROCESO':
            return 'primary'
        case 'PAUSADO':
            return 'warning';
        case 'PENDIENTE':
            return 'secondary';
        case 'CANCELADO':
            return 'danger';
        default:
            return 'light';
    }
};

const getStatusIcon = (status) => {
    switch (status) {
      case 'COMPLETADO':
        return '✅';
      case 'EN_PROCESO':
        return '🔄';
      case 'PAUSADO':
        return '⏸️';
      case 'PENDIENTE':
        return '⏳';
      case 'CANCELADO':
        return '❌';
      default:
        return '❔';
    }
};

const StatusBadge = ({ 
  status, 
  showIcon = true, 
  className = '', 
  style = {} 
}) => {
  return (
    <Badge 
      bg={getStatusColor(status)}
      className={className}
      style={style}
    >
      {showIcon && `${getStatusIcon(status)} `}
      {status}
    </Badge>
  );
};

export default StatusBadge;