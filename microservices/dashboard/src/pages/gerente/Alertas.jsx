import React from 'react';
import AlertasView from '../../components/shared/AlertasView';

// El Gerente visualiza alertas pero no reconoce/resuelve (eso es del Técnico).
const Alertas = () => <AlertasView canManage={false} />;

export default Alertas;
