# -*- coding: utf-8 -*-

# 原文件存放目录
# type = str
# 例如: "/home/ec2-user/srcdata"
srcdir = "<目录路径>"

# 指定要上传的文件的文件名(不含路径)
# type = str
# 例如 "myfile.mov"
# Upload全部文件则用 "*"
srcfileIndex = "*"

Megabytes = 1024*1024

# 文件分片大小，不小于5M
# 注意S3限制单文件分片总数不能超过10000
# type = int
# 例如: 100*Megabytes
# 对于上传几十GB的大文件，推荐分片大小为100*Megabytes
chunksize = 10*Megabytes

# 分拆文件的临时目录
# 如果要重新上传，删除该目录下的ini文件即可
# type = str
# 例如 "/tmp"
splitdir = "<目录路径>"

# S3 bucket
# type = str
# 例如: "mybucket2020"
s3bucket = "<Bucket Name>"

# S3 目录前缀 prefix (不含文件名)
# type = str
# 例如 "multipart/"
s3key = "multipart/"

# 单个Part上传失败最大重试次数
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
