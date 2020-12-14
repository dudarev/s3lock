from s3lock import S3Lock


s3lock = S3Lock('s3lock-test-bucket')

print(s3lock.is_locked('test2'))

# lock for 10 seconds
print(s3lock.is_locked('test'))
s3lock.lock('test', 'test', 10000)
print(s3lock.is_locked('test'))

# s3lock.unlock('test', 'test')
# print(s3lock.will_be_locked_for('test', 'test', 10000))
