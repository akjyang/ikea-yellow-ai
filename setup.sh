#!/usr/bin/env bash

gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable bigquerydatatransfer.googleapis.com

bq mk --force=true --dataset ikea_yellow

bq mk \
  --transfer_config \
  --data_source=cross_region_copy \
  --target_dataset=ikea_yellow \
  --display_name='SQL Talk Sample Data' \
  --schedule_end_time="$(date -u -d '5 mins' +%Y-%m-%dT%H:%M:%SZ)" \
  --params='{
      "source_project_id":"ingka-ushub-whartonfy25-test",
      "source_dataset_id":"ikea_yellow",
      "overwrite_destination_table":"true"
      }'

export PYTHON_PREFIX=~/miniforge
curl -Lo ~/miniforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash ~/miniforge.sh -fbp ${PYTHON_PREFIX}
rm -rf ~/miniforge.sh

${PYTHON_PREFIX}/bin/pip install -r requirements.txt

${PYTHON_PREFIX}/bin/streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080