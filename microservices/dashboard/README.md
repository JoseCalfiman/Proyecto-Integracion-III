Responsable: Alexis Monsalve

Aplicación en Streamlit que muestra gráficos en tiempo real de temperatura y consumo eléctrico, una tabla de alertas históricas, y una sección de chat donde el gerente puede consultar a Gemini sobre el estado de las cámaras.


 dashboard/                     # Dashboard (Alexis y José) - React + Tailwind
│       ├── Dockerfile
│       ├── nginx.conf                 # Configuración de Nginx para servir React
│       ├── package.json               # Dependencias de Node.js
│       ├── tailwind.config.js         # Configuración de Tailwind CSS
│       ├── postcss.config.js          # Configuración de PostCSS
│       ├── index.html                 # HTML principal
│       ├── src/ (ALEXIS)
│       │   ├── App.jsx                # Componente principal
│       │   ├── main.jsx               # Punto de entrada de React
│       │   ├── index.css              # Estilos globales (Tailwind)
│       │   ├── api/ (JOSÉ)
│       │   │   ├── client.js          # Cliente HTTP (axios)
│       │   │   ├── auth.js            # Funciones de autenticación
│       │   │   ├── alertas.js         # Funciones de alertas
│       │   │   ├── camaras.js         # Funciones de cámaras
│       │   │   ├── haccp.js           # Funciones de HACCP
│       │   │   ├── optimizacion.js    # Funciones de optimización
│       │   │   └── historial.js       # Funciones de historial
│       │   ├── components/ (JOSÉ)
│       │   │   ├── layout/
│       │   │   │   ├── Sidebar.jsx    # Barra lateral de navegación
│       │   │   │   ├── Header.jsx     # Barra superior
│       │   │   │   └── Layout.jsx     # Layout principal
│       │   │   ├── ui/
│       │   │   │   ├── Card.jsx       # Tarjeta reutilizable
│       │   │   │   ├── Button.jsx     # Botón reutilizable
│       │   │   │   ├── Input.jsx      # Input reutilizable
│       │   │   │   ├── Select.jsx     # Select reutilizable
│       │   │   │   ├── Switch.jsx     # Toggle switch reutilizable
│       │   │   │   └── Slider.jsx     # Slider reutilizable
│       │   │   └── charts/
│       │   │       ├── TemperatureChart.jsx  # Gráfico de temperatura (Chart.js o Recharts)
│       │   │       └── ConsumptionChart.jsx  # Gráfico de consumo
│       │   ├── pages/ (ALEXIS)
│       │   │   ├── Login.jsx          # Página de login
│       │   │   ├── Dashboard.jsx      # Página de monitoreo en vivo
│       │   │   ├── Alertas.jsx        # Página de alertas HACCP
│       │   │   ├── Ahorro.jsx         # Página de optimización y ahorro
│       │   │   ├── ChatIA.jsx         # Página de asistente IA (Gemini)
│       │   │   ├── Camaras.jsx        # Página de configuración de cámaras
│       │   │   ├── HACCP.jsx          # Página de reglas HACCP
│       │   │   ├── Usuarios.jsx       # Página de gestión de usuarios
│       │   │   └── Historial.jsx      # Página de historial y reportes
│       │   ├── hooks/ (ALEXIS)
│       │   │   ├── useAuth.js         # Hook de autenticación
│       │   │   └── useApi.js          # Hook para llamadas a la API
│       │   ├── context/ (ALEXIS)
│       │   │   └── AuthContext.jsx    # Contexto de autenticación (React Context)
│       │   └── utils/ (ALEXIS)
│       │       ├── formatters.js      # Formateadores de fechas, números, etc.
│       │       └── validators.js      # Validadores de formularios
│       ├── public/
│       │   ├── favicon.ico
│       │   └── logo.svg
│       ├── tests/ # AMBOS
│       │   ├── test_dashboard.js
│       │   └── test_api.js
│       └── __init__.py