# -*- coding: utf-8 -*-

# 原文件存放Region, type = str
srcRegion = "cn-north-1"
# 原文件存放bucket, type = str
srcBucket = "<yourbucket>"
# 原文件存放S3目录前缀, type = str
srcPrefix = "multipart/"
# 指定要上传的文件的文件名, type = str，Upload全部文件则用 "*"
srcfileIndex = "*"

# 访问源S3的access key id
src_aws_access_key_id = "<id>" # 例如 "AAAAAAAAAAAAAAAAAAAAAAAA"
src_aws_secret_access_key = "<key>" # 例如 "AAAAAAAAAAAAAAAAAAAAAAAA"

Megabytes = 1024*1024
# 文件分片大小，不小于5M，单文件分片总数不能超过10000, type = int
chunksize = 10*Megabytes

# 存储上传UploadID的本地临时目录, type = str
# 如果要重新上传，删除该目录下的ini文件即可
# 例如 "/tmp"
uploadIDdir = "<dir>"

# 目标文件存放Region, type = str
desRegion = "us-west-2"

# 目标文件bucket, type = str
# 例如 "mybucket2020"
desBucket = "<yourbucket>"

# 访问目标S3的access key id
des_aws_access_key_id = "<id>" # 例如 "AAAAAAAAAAAAAAAAAAAAAAAA"
des_aws_secret_access_key = "<key>" # 例如 "AAAAAAAAAAAAAAAAAAAAAAAA"

# 单个Part下载和上传失败最大重试次数
# type = int
# 例如: 30
MaxRetry = 30

# Python多线程上传，同时上传的线程数量
# type = int
# 例如：3
MaxThread = 3

# 是否跳过小于chunksize的小文件
# 数字0为不跳过, 为1则跳过
# type = int
IgnoreSmallFile = 0
