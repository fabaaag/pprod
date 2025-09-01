import React from 'react';
import { ProgressBar as BootstrapProgressBar } from 'react-bootstrap';

const getProgressVariant = (percentage, isOverProduction = false) => {
    if (isOverProduction) return 'warning';
    if (percentage >= 100) return 'success';
    if (percentage >= 75) return 'info';
    if (percentage >= 50) return 'warning';
    return 'danger';
}

const ProgressBar = ({
    current,
    total,
    showLabel = true,
    showValues = true,
    height = '20px',
    className = '',
    style = {}
}) => {
    const percentage = total > 0 ? (current / total  * 100) : 0;
    const isOverProduction = percentage > 100;

    return (
        <div className={className}>
            {showValues && (
                <div className="d-flex justify-content-between mb-1">
                    <small>{current} / {total}</small>
                    <small>{percentage.toFixed(1)}%</small>
                </div>
            )}
            <BootstrapProgressBar 
                now={Math.min(percentage, 100)}
                variant={getProgressVariant(percentage, isOverProduction)}
                label={showLabel ? `${percentage.toFixed(1)}%` : undefined}
                style={{
                    height,
                    ...style
                }}
            />
            {isOverProduction && (
                <small className ="text-warning mt-1">
                   ⚠️ Sobreproducción: +{(percentage - 100).toFixed(1)}%
                </small>
            )}
        </div>
    );
};

export default ProgressBar;