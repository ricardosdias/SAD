pip:
	@pip install -r requirements.txt

run_anomaly_detector_pipeline:
	@python -m sofia_anomaly_detector.services.anomaly_detector_pipeline

deploy_dev:
	tsuru app-deploy -a sofia-anomaly-detector-dev .

deploy_prod:
	tsuru app-deploy -a sofia-anomaly-detector .