AWS_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca
AWS_DESTINATION=s3://ami-trapdata/michael/oahu/
export PYTHONHTTPSVERIFY=0

aws s3 ls --endpoint-url $AWS_ENDPOINT_URL $AWS_DESTINATION --no-verify
aws s3 ls --endpoint-url $AWS_ENDPOINT_URL s3://ami-trapdata/michael/oahu/2025-02-13/ --no-verify

LOCAL_DIR=/home/pi/Desktop/Mothbox/photos/2025-02-12
aws s3 sync --endpoint-url $AWS_ENDPOINT_URL $LOCAL_DIR $AWS_DESTINATION --no-verify-ssl


