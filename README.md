# Sophia Anomaly Detection System

![Sophia Anomaly Detection Architecture](./SophiaAnomalyDetection.png?raw=true "Sophia Anomaly Detection Architecture")

## Collector Module

We use [Telegraf](https://www.influxdata.com/time-series-platform/telegraf/) and [Apache Kafka](https://kafka.apache.org/) to build the collector module. Telegraf is an agent for collecting, aggregating, processing, and sending metrics. Through plugins it integrates with a wide variety of systems. Apache Kafka is a distributed streaming platform for a large volume of data flow so that we can use it to publish, store, process, and consume messages in real-time.

We install the Telegraf agent on each monitored machine to get metrics such as CPU, networking, memory, disk I/O, disk size, OS load, database connections, among others. The Telegraf agent sends the collected metrics to Apache Kafka that temporarily stores them to be consumed by other applications.

## Processing Module

The processing module analyzes metrics, instantiates the anomaly detection algorithm ([DASRS Rest](https://github.com/ricardosdias/DASRS)), and sends the anomaly scores and alarms to the visualization module. The Anomaly Detection API reads the raw metrics from Apache Kafka. Since the Kafka's messages are complex data structures, the API parses them. As illustrated in interaction 1, the API performs filter, split, mapping, among others operations on the raw metrics to identify each type of metric collected, and assemble the data structure expected for the anomaly detection algorithm, that is, a time series (Interaction 2).

If Sophia's anomaly detection API receives CPU and network metrics from three Virtual Machines (VMs), for instance, it will create six different time series: VM1-CPU, VM2-CPU, VM3-CPU, VM1-Network, VM2-Network, and VM3-Network. Besides, to process multiple metrics of several VMs, Sophia's API uses multiple instances of the anomaly detection algorithm DASRS. One DASRS instance for each time series. Therefore, in the example above, the anomaly detection API will instantiate 6 DASRS instances, and each of them will receive the streaming values collected from its time series in an orderly manner.

DASRS algorithms generate an anomaly score for each observation in the time series analyzed. Then, the API compares the anomaly score with a threshold to decide whether to generate an anomaly alarm or not. However, no one anomaly alarm is generated during the training period. Interaction 3 shows that we store the status of each DASRS instance in a [Redis](https://redis.io/) database. When analyzing a time series for the first time, Sophia's anomaly detection API creates a new instance of DASRS algorithm. Contrarily, when analyzing the same time series for a second time, Sophia's anomaly detection API loads the DASRS instance from the previously-stored (Interaction 4) detector's status. This way, it can continue the analyzes of that particular time series, even after a processing interruption for maintenance reasons.

## Visualization Module

Sophia's anomaly detection API generates anomaly alarms on [Zabbix](https://www.zabbix.com/) (Interaction 5), and sends anomaly scores to the Apache Kafka in the visualization module (Interaction 6). The Telegraf agent in this module reads the anomaly scores from Kafka and sends them to a [TimeScale](https://www.timescale.com/) database to be persisted.

System administrators can get all anomaly alarm generated by DASRS through Zabbix. They also can analyze the anomaly detections through [Grafana](https://grafana.com/).

TimeScale is a relational database designed to store time series data, providing automatic time partitioning; Zabbix is an open-source monitoring software tool; and Grafana is a platform for visualizing and analyzing metrics through graphs.

We implement the Sophia System using [Tsuru](https://tsuru.io/). Tsuru is a Platform as a Service (PaaS). Using Tsuru, we easily deploy, scale, and manage either the API as well as DASRS.

## Reference

This readme is a brief overview. For more details about DASRS, see the following paper:

* [Toward an Efficient Real-Time Anomaly Detection System for Cloud Datacenters](https://ieeexplore.ieee.org/abstract/document/9142768)

#### Publication in Portuguese

* [Detecção de anomalias nas métricas das monitorações de máquinas de um data center](https://www.maxwell.vrac.puc-rio.br/colecao.php?strSecao=resultado&nrSeq=46523@1)