import json
import logging
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logger = logging.getLogger("monitoring_service")

class MockProducer:
    def __init__(self):
        logger.info("Initializing MOCK Kafka Producer (Offline Fallback)")

    def send(self, topic, value):
        # Helper to show simulation outputs in mock mode if needed
        # We write it to a debug or print, but we don't spam the console logs
        # unless it is failure event, which we might want to see clearly.
        pass

    def flush(self):
        pass

    def close(self):
        pass

class KafkaProducerWrapper:
    def __init__(self, bootstrap_servers):
        self.producer = None
        self.offline = False
        try:
            logger.info(f"Connecting to Kafka brokers: {bootstrap_servers}")
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                acks='all',
                request_timeout_ms=3000,
                max_block_ms=3000
            )
            logger.info("Successfully connected to Kafka cluster.")
        except NoBrokersAvailable:
            logger.warning("Kafka brokers not available. Falling back to Mock Producer.")
            self.producer = MockProducer()
            self.offline = True
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka ({e}). Falling back to Mock Producer.")
            self.producer = MockProducer()
            self.offline = True

    def send_message(self, topic, message):
        try:
            if not self.offline:
                # kafka-python send is asynchronous, returns a FutureRecordMetadata
                self.producer.send(topic, message)
            else:
                self.producer.send(topic, message)
        except Exception as e:
            logger.error(f"Error publishing message to {topic}: {e}")

    def flush(self):
        if self.producer:
            self.producer.flush()

    def close(self):
        if self.producer:
            self.producer.close()
