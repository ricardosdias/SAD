pip:
	@pip install -r requirements.txt

run_anomaly_detector_pipeline:
	@python -m sophia_anomaly_detector.services.anomaly_detector_pipeline

deploy_dev:
	tsuru app-deploy -a sophia-anomaly-detector-dev .

deploy_prod:
	tsuru app-deploy -a sophia-anomaly-detector .