"""
Experiments with s3 client
"""

import boto3
from boto3_type_annotations.s3 import Client
from datetime import datetime

s3_client: Client = boto3.client('s3')

BUCKET = 's3lock-test-bucket'

# response = s3_client.put_object(
#     Bucket=BUCKET,
#     Key='test-version',
#     Body=datetime.utcnow().isoformat().encode('utf-8')
# )
# print(response)

response = s3_client.list_object_versions(
    Bucket=BUCKET,
    Prefix='test-version'
)
print(response)

# response = s3_client.delete_object(
#     Bucket=BUCKET,
#     Key='test-version'
# )

pass
