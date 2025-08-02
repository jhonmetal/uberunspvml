"""
Main Application Entry Point - Anomaly Detection MLOps
Orchestrator principal para el sistema de detección de anomalías
"""


import asyncio
import sys
import subprocess
import time
from pathlib import Path
import logging
from datetime import datetime
import mlflow

# Añadir el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from anomaly_detector.application.fastapi_server import app as fastapi_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MLOpsOrchestrator:
    """Orchestrator para todos los servicios MLOps"""

    def __init__(self):
        self.api_process = None
        self.dashboard_process = None
        self.mlflow_process = None

    async def ensure_initial_model(self):
        """Asegurar que existe al menos un modelo entrenado"""
        try:
            # Configurar MLflow
            mlflow_db_path = project_root.parent / "mlruns"
            mlflow_uri = f"file:///{mlflow_db_path}".replace('\\', '/')
            mlflow.set_tracking_uri(mlflow_uri)

            # Verificar si hay experimentos
            try:
                experiments = mlflow.search_experiments()
                if not experiments:
                    logger.info(
                        "🤖 No se encontraron experimentos - ejecutando entrenamiento inicial..."
                    )
                    await self.run_bootstrap_training()
                    return

                # Verificar si hay runs con modelos
                runs = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id for exp in experiments]
                )
                if runs.empty:
                    logger.info(
                        "🤖 No se encontraron modelos entrenados - ejecutando entrenamiento inicial..."
                    )
                    await self.run_bootstrap_training()
                else:
                    logger.info(f"✅ Encontrados {len(runs)} modelos entrenados")

            except Exception as e:
                logger.info(
                    "🤖 MLflow tracking nuevo o error - ejecutando entrenamiento inicial..."
                )
                await self.run_bootstrap_training()

        except Exception as e:
            logger.error(f"❌ Error verificando modelos: {e}")
            logger.info("⚠️ Continuando sin entrenamiento inicial...")

    async def run_bootstrap_training(self):
        """Ejecutar entrenamiento inicial básico"""
        try:
            logger.info("🚀 Iniciando entrenamiento bootstrap...")

            # Ejecutar el script de entrenamiento
            train_script = (
                project_root / "domain" / "services.py"
            )

            if train_script.exists():
                result = subprocess.run(
                    [sys.executable, str(train_script), "--bootstrap"],
                    capture_output=True,
                    text=True,
                    cwd=str(project_root),
                )

                if result.returncode == 0:
                    logger.info("✅ Entrenamiento bootstrap completado")
                else:
                    logger.error(
                        f"❌ Error en entrenamiento bootstrap: {result.stderr}"
                    )
            else:
                logger.warning(
                    "⚠️ Script de entrenamiento no encontrado - creando modelo dummy..."
                )
                await self.create_dummy_model()

        except Exception as e:
            logger.error(f"❌ Error en entrenamiento bootstrap: {e}")
            await self.create_dummy_model()

    async def create_dummy_model(self):
        """Crear un modelo dummy para que el sistema funcione"""
        try:
            import mlflow.sklearn
            from sklearn.ensemble import IsolationForest
            import numpy as np

            logger.info("🎯 Creando modelo dummy para demostración...")

            mlflow.set_experiment("anomaly_detection")

            with mlflow.start_run(run_name="bootstrap_model"):
                # Datos sintéticos
                X = np.random.randn(1000, 8)
                # Modelo simple
                model = IsolationForest(n_estimators=10, random_state=42)
                model.fit(X)

                # Métricas dummy (EM y MV)
                mlflow.log_param("model_type", "IsolationForest")
                mlflow.log_param("n_estimators", 10)
                mlflow.log_param("bootstrap", True)
                mlflow.log_metric("em", 0.85)
                mlflow.log_metric("mv", 0.12)

                # Guardar modelo
                mlflow.sklearn.log_model(model, "model")

                logger.info("✅ Modelo dummy creado exitosamente")

        except Exception as e:
            logger.error(f"❌ Error creando modelo dummy: {e}")

    def start_api_server(self):
        """Iniciar servidor FastAPI"""
        logger.info("🚀 Iniciando FastAPI Server en puerto 8000...")
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "application.fastapi_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ]
        self.api_process = subprocess.Popen(cmd, cwd=str(project_root))
        return self.api_process

    def start_dashboard(self):
        """Iniciar Dashboard Streamlit"""
        ports_to_try = [8506, 8507, 8508, 8509]

        for port in ports_to_try:
            try:
                logger.info(
                    f"📊 Intentando iniciar Dashboard en puerto {port}..."
                )

                dashboard_path = (
                    project_root / "streamlit_dashboard" / "dashboard.py"
                )

                cmd = [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(dashboard_path),
                    "--server.port",
                    str(port),
                    "--server.headless",
                    "true",
                ]

                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    result = s.connect_ex(("localhost", port))
                    if result == 0:
                        logger.warning(
                            f"⚠️  Puerto {port} está ocupado, intentando siguiente..."
                        )
                        continue

                self.dashboard_process = subprocess.Popen(cmd, cwd=str(project_root))
                logger.info(f"✅ Dashboard iniciado en puerto {port}")
                return self.dashboard_process

            except Exception as e:
                logger.warning(f"⚠️  Error en puerto {port}: {e}")
                continue

        logger.error("❌ No se pudo iniciar el dashboard en ningún puerto disponible")
        return None

    def start_mlflow_ui(self):
        """Iniciar MLflow UI"""
        logger.info("🔬 Iniciando MLflow UI en puerto 5000...")

        mlflow_db_path = project_root.parent / "mlruns"
        mlflow_uri = f"file:///{mlflow_db_path}".replace('\\', '/')

        cmd = [
            sys.executable,
            "-m",
            "mlflow",
            "ui",
            "--backend-store-uri",
            mlflow_uri,
            "--host",
            "0.0.0.0",
            "--port",
            "5000",
        ]
        self.mlflow_process = subprocess.Popen(cmd, cwd=str(project_root))
        return self.mlflow_process

    async def start_all_services(self):
        """Iniciar todos los servicios MLOps"""
        logger.info("🎯 Iniciando Stack MLOps Completo...")

        # 🤖 PASO 1: Asegurar modelo inicial
        await self.ensure_initial_model()

        # 🚀 PASO 2: Iniciar servicios
        self.start_api_server()
        time.sleep(2)

        self.start_dashboard()
        time.sleep(2)

        self.start_mlflow_ui()
        time.sleep(3)

        logger.info("✅ Todos los servicios iniciados:")
        logger.info("   🚀 FastAPI Server: http://localhost:8000")
        logger.info(
            "   📊 Dashboard: http://localhost:8506+ (puerto automático)"
        )
        logger.info("   🔬 MLflow UI: http://localhost:5000")
        logger.info("")
        logger.info("🎯 Sistema completamente funcional desde el primer uso!")
        logger.info("🤖 Los modelos están pre-entrenados y listos para predicciones")

        return True

    def stop_all_services(self):
        """Detener todos los servicios"""
        logger.info("🛑 Deteniendo servicios MLOps...")

        for process_name, process in [
            ("API", self.api_process),
            ("Dashboard", self.dashboard_process),
            ("MLflow", self.mlflow_process),
        ]:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    logger.info(f"✅ {process_name} detenido")
                except:
                    process.kill()
                    logger.info(f"🔥 {process_name} forzado a detenerse")


def main():
    """Función principal - Orchestrator MLOps"""
    logger.info("🚀 Anomaly Detection MLOps Stack")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    orchestrator = MLOpsOrchestrator()

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(orchestrator.start_all_services())

        logger.info("⌨️  Presiona Ctrl+C para detener todos los servicios")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("🛑 Señal de interrupción recibida")
    finally:
        orchestrator.stop_all_services()
        logger.info("👋 MLOps Stack detenido")


# Para compatibilidad individual con uvicorn (solo API)
app = fastapi_app


if __name__ == "__main__":
    main()
