import json
from datetime import datetime, timedelta
from typing import Optional

import boto3
from boto3_type_annotations.s3 import Client
from botocore.exceptions import ClientError
from dataclasses import dataclass, asdict


@dataclass
class LockData:
    lock_owner: str
    resource_name: str
    duration_ms: int
    expires_at: Optional[str] = None  # UTC ISO 8601 string with Z appended

    def __post_init__(self):
        # if no `expires_at` is specified at initialization, it's set to `utcnow + duration_ms`.
        self.expires_at = self.expires_at or \
                          (datetime.utcnow() + timedelta(milliseconds=self.duration_ms)).isoformat() + "Z"

    @classmethod
    def from_str(cls, s: str) -> 'LockData':
        return LockData(**json.loads(s))

    def to_str(self) -> str:
        return json.dumps(asdict(self))

    @property
    def is_locked(self):
        if not self.expires_at:
            return False
        if datetime.utcnow().isoformat() + "Z" < self.expires_at:
            return True
        return False


class S3Lock:

    def __init__(self, s3_bucket: str, prefix: str = '', suffix: str = '.lock', s3_client=None):
        """ Initialize S3Lock with
        :param s3_bucket: S3 bucket to hold the locks
        :param prefix: optional prefix to add to all lock keys
        :param suffix: suffix added to all lock keys, by default it's '.lock'
        :param s3_client: optional s3_client, if not specified it's created
        """
        self.s3_bucket = s3_bucket
        self.prefix = prefix
        self.suffix = suffix
        if not self.prefix and not self.suffix:
            raise ValueError("At least prefix or suffix must by specified for S3Lock")
        if not s3_client:
            self.s3_client: Client = boto3.client('s3')
        else:
            self.s3_client: Client = s3_client

    def _get_lock_data(self, resource_name) -> Optional[LockData]:
        try:
            data = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self._get_resource_lock_key(resource_name)
            )['Body'].read().decode('utf-8')
            data = LockData.from_str(data)
            return data
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchKey':
                # no lock file exists
                return None
            else:
                raise ex

    def _get_resource_lock_key(self, resource_name: str):
        return self.prefix + resource_name + self.suffix

    def is_locked(self, resource_name: str):
        lock_data = self._get_lock_data(resource_name)
        if lock_data is None:
            return False
        return lock_data.is_locked

    def lock(self, lock_owner: str, resource_name: str, duration_ms: int) -> bool:
        """
        Lock `resource_name` for `duration_ms` milliseconds
        :param lock_owner: lock owner
        :param resource_name: resource to be locked
        :param duration_ms: duration for lock in milliseconds
        :return: `True` if locked successfully, `False` otherwise
        """
        if self.is_locked(resource_name):
            return False
        data = LockData(lock_owner=lock_owner, resource_name=resource_name, duration_ms=duration_ms)
        self.s3_client.put_object(
            Body=data.to_str().encode('utf-8'),
            Bucket=self.s3_bucket,
            Key=self._get_resource_lock_key(resource_name)
        )
        return True

    def unlock(self, lock_owner: str, resource_name: str) -> bool:
        """
        :param lock_owner: lock owner who is attempting to unlock resource, it must be the same as current lock owner
        :param resource_name: resource name
        :return: `True` if was unlocked successfully, `False` otherwise
        """
        if not self.is_owned(lock_owner, resource_name):
            return False
        self.s3_client.delete_object(
            Bucket=self.s3_bucket,
            Key=self._get_resource_lock_key(resource_name)
        )
        return True

    def is_owned(self, lock_owner: str, resource_name: str) -> bool:
        lock_data = self._get_lock_data(resource_name)
        return lock_data.lock_owner == lock_owner

    def is_owned_and_will_be_locked_for(
            self, lock_owner: str, resource_name: str, time_ms: int) -> bool:
        lock_data = self._get_lock_data(resource_name)
        t = (datetime.utcnow() + timedelta(milliseconds=time_ms)).isoformat() + "Z"
        return lock_data.lock_owner == lock_owner and lock_data.expires_at > t
