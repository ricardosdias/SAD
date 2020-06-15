pip:
	@pip install -r requirements.txt

run_anomaly_detector_pipeline:
	@python -m spphia_anomaly_detector.services.anomaly_detector_pipeline

deploy_dev:
	tsuru app-deploy -a spphia-anomaly-detector-dev .

deploy_prod:
	tsuru app-deploy -a spphia-anomaly-detector .