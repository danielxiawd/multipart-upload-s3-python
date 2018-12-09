# -*- coding: utf-8 -*-

# 在~/.aws 中配置的 profile name，定义了访问 源S3 的 credentials
src_aws_profile_name = "default"  
# 原文件存放bucket, type = str
srcBucket = "<yourbucket>"
# 原文件存放S3目录前缀, type = str
srcPrefix = "multipart/"
# 指定要上传的文件的文件名, type = str，Upload全部文件则用 "*"
srcfileIndex = "*"

Megabytes = 1024*1024
# 文件分片大小，不小于5M，单文件分片总数不能超过10000, type = int
chunksize = 10*Megabytes
# 注意！！！如果某个文件传输到一半，要修改chunksize。请中断，然后
# 在启动时选择Clean unfinished upload，程序会清除未完成文件，并重新上传整个文件

# 在~/.aws 中配置的 profile name，定义了访问 目的S3 的 credentials
des_aws_profile_name = "oregon"
# 目标文件bucket, type = str
# 例如 "mybucket2020"
desBucket = "<yourbucket>"

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
