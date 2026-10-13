# React + Vite

feature/dashboard
This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.


develop
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

