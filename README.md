# ⚽ Ticket Fútbol - Plataforma de Boletería Deportiva

Ticket Fútbol es una solución transaccional premium para la venta y control de acceso a partidos de fútbol, diseñada con una arquitectura moderna de microservicios, procesamiento de colas asíncronas y simulación serverless.

## 🌟 Características Clave
* **Próximos Eventos (Mundial 2026)**: Vista cliente precargada con partidos mundialistas icónicos (Argentina vs Francia, Brasil vs Alemania, España vs Italia) y selección dinámica de asientos en estadio elíptico.
* **Control de Acceso con Cámara**: Escáner en tiempo real integrado para el Personal de Acceso (Staff). Lee códigos QR directamente usando la cámara del celular y valida la autenticidad al instante.
* **Limpiador de UUID Inteligente**: Si se copia el enlace completo del boleto (`/t/uuid`), el escáner extrae el UUID de manera automática para evitar errores humanos.
* **Historial y Gestión de Eventos**: Panel para Organizadores (Admin) para ver todos los partidos creados, editarlos, eliminarlos en cascada, o alternar su visibilidad (Visible/Oculto) para los clientes.
* **Simulador de Roles**: Selector superior dinámico que permite a la cuenta `admin` alternar su rol simulado en tiempo real entre Organizador y Staff.

---

## 🛠️ Stack Tecnológico
1. **API Gateway & Router**: FastAPI (Python 3.10) + Uvicorn.
2. **Base de Datos**: PostgreSQL 15 (Eventos, Usuarios, Órdenes, Asientos y Boletos).
3. **Caché y Colas**: Redis 7 (Límites transaccionales con Locks en memoria y bróker de Celery).
4. **Colas Asíncronas**: Celery Worker (Generación diferida de imágenes QR).
5. **Serverless (AWS Lambdas simuladas)**:
   - `PaymentProcessor`: Simula la captura en pasarela de pagos.
   - `TicketGenerator`: Genera los QRs vinculados al enlace único del boleto.
6. **Frontend**: Dashboard con estilo glassmorphism (HTML5/Jinja2/Vanilla CSS/JS) y librerías HTML5-QRCode.

---

## 🚀 Cómo Correr el Proyecto en tu Computadora

### Requisitos Previos
Tener instalados **Docker** y **Docker Compose** en tu sistema.

### Instrucciones de Despliegue Rápido
1. Descarga o clona el proyecto e ingresa a la carpeta raíz.
2. Construye e inicia todos los contenedores en segundo plano:
   ```bash
   docker compose -f docker/docker-compose.yml up --build -d
   ```
3. Verifica que todos los servicios estén activos y saludables:
   ```bash
   docker compose -f docker/docker-compose.yml ps
   ```
4. Abre los siguientes enlaces en tu navegador:
   * **Portal de Boletería y Administración**: [http://localhost:8000/](http://localhost:8000/)
   * **Documentación Interactiva (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   * **Simulador de Lambdas**: [http://localhost:8001/docs](http://localhost:8001/docs)

---


## 🧪 Pruebas Unitarias Locales (Opcional)

Si deseas correr los tests lógicos locales de integración sin usar Docker:
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecuta el suite de pruebas de flujo:
   ```bash
   python -m unittest tests/test_flow.py
   ```
