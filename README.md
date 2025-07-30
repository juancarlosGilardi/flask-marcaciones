# 🚀 HISPE PULSE - Sistema de Marcaciones

## 📋 Descripción
Sistema de marcaciones web desarrollado en Flask para HISPE SAC.

## 🛠️ Instalación

1. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
El archivo `.env` ya está configurado con las credenciales correctas.

4. **Ejecutar aplicación:**
```bash
python app.py
```

5. **Abrir navegador:**
http://localhost:5000

## 🎯 Funcionalidades

- ✅ Marcación de INGRESO
- ✅ Scanner QR web
- ✅ Input manual de QR
- ✅ Datos MOCK para testing
- ✅ UI responsive
- ✅ API REST

## 🏗️ Estructura del proyecto

```
flask-marcaciones/
├── app.py                 # 🎯 API principal
├── .env                   # 🔐 Credenciales
├── requirements.txt       # 📋 Dependencias
├── static/
│   ├── css/
│   │   └── style.css     # 🎨 Estilos
│   └── js/
│       └── app.js        # ⚡ JavaScript
└── templates/
    └── index.html        # 🌐 Frontend
```

## 📊 Usuario MOCK
- **Nombre:** Juan Carlos Pérez
- **Email:** juan.perez@hispe.com
- **DNI:** 12345678

## 📍 Ubicación MOCK
- **Latitud:** -12.0464
- **Longitud:** -77.0428
- **Dirección:** Lima, Perú - Oficina Principal

## 🚀 Para desarrollo
```bash
# Activar modo debug
export FLASK_DEBUG=True
python app.py
```
