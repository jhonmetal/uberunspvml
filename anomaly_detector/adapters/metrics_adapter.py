"""
MetricsAdapter implements Prometheus metrics collection for monitoring.
"""

from prometheus_client import Counter, Histogram



class MetricsAdapter:
    def __init__(self):
        self.batch_predict_latency = Histogram('batch_predict_latency_seconds', 'Batch prediction latency')
        self.batch_predict_count = Counter('batch_predict_count', 'Batch prediction requests')
        self.batch_predict_errors = Counter('batch_predict_errors', 'Batch prediction errors')

    def observe_latency(self, value):
        self.batch_predict_latency.observe(value)

    def inc_count(self):
        self.batch_predict_count.inc()

    def inc_error(self):
        self.batch_predict_errors.inc()
