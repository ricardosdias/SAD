import logging
import datetime
import json
from redis.sentinel import Sentinel
import pickle
from confluent_kafka import Consumer, KafkaError, Producer
from sophia_anomaly_detector.detector.dasrs import DASRS
from sophia_anomaly_detector.settings import (
    KAFKA_SERVERS,
    KAFKA_MESSAGE_CONSUMER_GROUP,
    KAFKA_MESSAGE_TOPIC,
    KAFKA_ANOMALY_TOPIC,
    DBAAS_SENTINEL_ENDPOINT_SIMPLE,
    DBAAS_SENTINEL_SERVICE_NAME,
    DBAAS_SENTINEL_PASSWORD,
    LOG_COUNT,
    LOGGING_LEVEL,
    REDIS_SOCKET_TIMEOUT)


logging.basicConfig(
    format='%(asctime)s %(filename)s(%(lineno)d) %(levelname)s: %(message)s')
LOG = logging.getLogger(__name__)
LOG.setLevel(LOGGING_LEVEL)


class AnomalyDetectorPipeline(object):

    def __init__(self):

        self.kafka_consumer = Consumer({
            'bootstrap.servers': KAFKA_SERVERS,
            'group.id': KAFKA_MESSAGE_CONSUMER_GROUP,
            'session.timeout.ms': 6000,
            'auto.offset.reset': 'latest'
        })
        self.kafka_consumer.subscribe([KAFKA_MESSAGE_TOPIC])
        LOG.info('Connected with Kafka Consumer')

        self.kafka_producer = Producer({
            'bootstrap.servers': KAFKA_SERVERS
        })
        LOG.info('Connected with Kafka Producer')

        hosts_sentinel = []
        endpoint = DBAAS_SENTINEL_ENDPOINT_SIMPLE.replace("sentinel://", "")
        for host in endpoint.split(','):
            hosts_sentinel.append(tuple(host.split(':')))
        sentinel = Sentinel(
            hosts_sentinel, socket_timeout=REDIS_SOCKET_TIMEOUT)
        self.rediscon = sentinel.master_for(
            DBAAS_SENTINEL_SERVICE_NAME,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            password=DBAAS_SENTINEL_PASSWORD)
        LOG.info('Connected with Redis Database')

    def main(self):
        msg_consumed_count = 0
        LOG.info('Message Pipeline Start')
        while True:
            message = self.kafka_consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                error = "Kafka consumer error: {}".format(message.error())
                LOG.error(error)
                continue
            metric = self.message2metric(message.value().decode('utf-8'))
            if metric['metric'] == 'cpu':
                self.handle_cpu_metric(metric)
            elif metric['metric'] == 'disk':
                self.handle_disk_metric(metric)
            msg_consumed_count += 1
            if msg_consumed_count == LOG_COUNT:
                self.kafka_producer.flush()
                msg = "{} messages read. Last metric collected at: {}".format(
                    msg_consumed_count, metric['time_collected'])
                LOG.info(msg)
                msg_consumed_count = 0

    def send_result(self, anomaly_result):
        output = "anomaly_score,host={},app={}".format(
            anomaly_result['host'],
            anomaly_result['app']
        )
        output += ",{}={},{}={},{}={},{}={}".format(
            'time_collected',
            anomaly_result['time_collected'].replace(' ', '\ '),
            'time_pipeline',
            anomaly_result['time_pipeline'].replace(' ', '\ '),
            'time_detector',
            anomaly_result['time_detector'].replace(' ', '\ '),
            'period_description',
            anomaly_result['period_description'].replace(' ', '\ ')
        )
        output += " value={},anomaly_score={},is_anomaly={} {}\n".format(
            anomaly_result['value'],
            anomaly_result['anomaly_score'],
            anomaly_result['is_anomaly'],
            anomaly_result['ts'],
        )

        self.kafka_producer.poll(0)
        self.kafka_producer.produce(
            KAFKA_ANOMALY_TOPIC, output.encode('utf-8'))

    def message2metric(self, message):
        tags, fields, ts = message.split(' ')
        metric = tags.split(',')[0]
        ts = ts.strip()

        tags_dict = {}
        for tag in tags.split(',')[1:]:
            key, value = tag.split('=')
            tags_dict[key] = value

        fields_dict = {}
        for field in fields.split(','):
            key, value = field.split('=')
            fields_dict[key] = value

        host = tags_dict.get('host')

        metric_dict = {
            'metric': metric,
            'ts': ts,
            'tags': tags_dict,
            'fields': fields_dict,
            'host': host,
            'time_collected': str(
                datetime.datetime.fromtimestamp(int(ts[:-9]))),
            'time_pipeline': str(datetime.datetime.now())
        }

        return metric_dict

    def handle_cpu_metric(self, data):
        if data['tags']['cpu'] != 'cpu-total':
            return
        usage_user = self.get_basic_metric_dict(data)
        usage_user.update({
            'app': 'dbaas.cpu.usage_user.{}'.format(data['host']),
            'value': float(data['fields']['usage_user']),
        })

        usage_system = self.get_basic_metric_dict(data)
        usage_system.update({
            'app': 'dbaas.cpu.usage_system.{}'.format(data['host']),
            'value': float(data['fields']['usage_system']),
        })

        usage_idle = self.get_basic_metric_dict(data)
        usage_idle.update({
            'app': 'dbaas.cpu.usage_idle.{}'.format(data['host']),
            'value': float(data['fields']['usage_idle']),
        })

        usage_iowait = self.get_basic_metric_dict(data)
        usage_iowait.update({
            'app': 'dbaas.cpu.usage_iowait.{}'.format(data['host']),
            'value': float(data['fields']['usage_iowait']),
        })

        self.analyze_metric(usage_user)
        self.analyze_metric(usage_system)
        self.analyze_metric(usage_idle)
        self.analyze_metric(usage_iowait)

    def handle_disk_metric(self, data):
        if data['tags']['path'] != '/data':
            return

        used_percent = self.get_basic_metric_dict(data)
        used_percent.update({
            'app': 'dbaas.disk.used_percent.{}'.format(data['host']),
            'value': float(data['fields']['used_percent']),
        })

        self.analyze_metric(used_percent)

    def get_basic_metric_dict(self, data):
        return {
            'host': data['host'],
            'ts': data['ts'],
            'time_collected': data['time_collected'],
            'time_pipeline': data['time_pipeline'],
        }

    def analyze_metric(self, data):
        app = data['app']
        ts = data['ts']
        imput_time = datetime.datetime.fromtimestamp(int(ts[:-9]))
        value = data['value']

        packed_object = self.rediscon.get(app)
        if packed_object:
            detector = pickle.loads(packed_object)
        else:
            detector = DASRS()

        anomaly_score = detector.getAnomalyScore(value, imput_time)
        period_description = detector.get_period_description()
        is_anomaly = detector.is_anomaly(anomaly_score)
        packed_object = pickle.dumps(detector)
        self.rediscon.set(app, packed_object)

        data.update({
            'anomaly_score': anomaly_score,
            'time_detector': str(datetime.datetime.now()),
            'is_anomaly': int(is_anomaly),
            'period_description': period_description
        })

        self.send_result(data)

if __name__ == '__main__':
    mp = AnomalyDetectorPipeline()
    mp.main()