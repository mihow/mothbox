AWS_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca
AWS_DESTINATION=s3://ami-trapdata/michael/oahu/
aws s3 ls --endpoint-url $AWS_ENDPOINT_URL $AWS_DESTINATION
aws s3 ls --endpoint-url $AWS_ENDPOINT_URL s3://ami-trapdata/michael/oahu/2025-02-13/


