from s3lock import S3Lock


def test_lock(s3):
    lock = S3Lock('test-bucket')
    # lock for 1 second
    assert lock.lock('test', 'test', 1000)
    data = s3.get_object(Bucket='test-bucket', Key='test.lock')['Body'].read().decode('utf-8')
    assert len(data)
