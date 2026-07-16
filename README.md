# ⚽ Ticket Fútbol - Plataforma de Boletería Deportiva

Ticket Fútbol es una solución transaccional premium para la venta y control de acceso a partidos de fútbol, diseñada con una arquitectura moderna de microservicios, procesamiento de colas asíncronas con **RabbitMQ**, caché distribuida y locks distribuidos con **Redis**, y un microservicio independiente de pagos (`ticket_payment_service`) comunicado vía HTTP REST.

> [!NOTE]
> ### 📋 Resumen del Proyecto y Ejecución Rápida
> 
> **¿De qué se trata?**  
> Es una plataforma web transaccional para la compra de boletos deportivos y validación de accesos en estadios mediante escaneo de códigos QR en tiempo real con la cámara del celular. Implementa locks distribuidos en memoria para prevenir la "doble venta" de asientos en partidos de alta concurrencia.
> 
> **¿Qué componentes contiene?**  
> * **ticket_api_gateway** (FastAPI, Puerto 8000): Gateway y portal principal.
> * **ticket_payment_service** (FastAPI, Puerto 8001): Microservicio de cobros con panel de telemetría en tiempo real.
> * **ticket_celery_worker** (Celery): Procesador de colas para generar códigos QR.
> * **ticket_rabbitmq**: Bróker de mensajería asíncrona.
> * **ticket_redis**: Base de datos in-memory para cierres (locks) y caché.
> * **ticket_db** (PostgreSQL 15): Base de datos persistente transaccional.
> 
> **¿Cómo correr el proyecto?**  
> Levanta todo el ecosistema de microservicios en segundo plano con un solo comando:
> ```bash
> docker compose -f docker/docker-compose.yml up --build -d
> ```
> * **Acceso Portal Web**: [http://localhost:8000/](http://localhost:8000/)
> * **Swagger API Gateway**: [http://localhost:8000/docs](http://localhost:8000/docs)
> * **Monitoreo de Pagos**: [http://localhost:8001/docs](http://localhost:8001/docs)
