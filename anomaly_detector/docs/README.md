# Documentación de Arquitectura y Diseño

## 📐 Arquitectura Hexagonal (Ports & Adapters)
La arquitectura hexagonal separa el núcleo de negocio (dominio) de las dependencias externas, permitiendo que el sistema sea fácilmente extensible, testeable y desacoplado.

### Diagrama Mermaid: Hexagonal
```mermaid
graph TD
    subgraph Dominio
        FE[Feature Engineering]
        AD[Anomaly Detection]
        SVC[Services]
        PORTS[Ports]
    end
    subgraph Adaptadores
        ML[MLflow Adapter]
        STG[Storage Adapter]
        MET[Metrics Adapter]
    end
    subgraph Aplicación
        API[FastAPI Server]
        DASH[Streamlit Dashboard]
    end
    FE --> AD
    AD --> SVC
    SVC --> PORTS
    PORTS -->|Implementación| ML
    PORTS -->|Implementación| STG
    PORTS -->|Implementación| MET
    API -->|Usa| PORTS
    DASH -->|Consulta| API
    ML -->|Registra| MLflow
    STG -->|Lee/Escribe| Parquet
    MET -->|Expone| Prometheus
```

---

## 🏛️ Domain-Driven Design (DDD)
- **Entidad principal:** Viaje Uber (Trip)
- **Agregado:** Detección de anomalías sobre agregados horarios y espaciales
- **Servicios de dominio:** Ingeniería de features, agregación, detección, visualización
- **Puertos:** Interfaces para almacenamiento, tracking, métricas, API
- **Adaptadores:** Implementaciones concretas para cada puerto

---

## 📊 Diagrama ER (Entidad-Relación)
```mermaid
erDiagram
    TRIP {
        string trip_id
        datetime timestamp
        float lat
        float lon
        string h3_index
        float value
        int is_anomaly
    }
    FEATURE {
        string feature_id
        string name
        string provenance
        datetime created_at
        float value
    }
    RUN {
        string run_id
        string model_type
        datetime start_time
        float training_time
        int train_size
        int num_anomalies
    }
    TRIP ||--o{ FEATURE : "tiene"
    RUN ||--o{ TRIP : "procesa"
    RUN ||--o{ FEATURE : "genera"
```

---

## 📝 Notas de Diseño
- Todos los modelos y features están versionados y auditados.
- Los artefactos y métricas se registran en MLflow.
- El dashboard consulta la API para obtener tendencias y salud del sistema.
- La seguridad y compliance se aplican en todos los componentes.

---

Para más detalles, consulta los diagramas y documentación en este folder y en los archivos fuente del repositorio.
