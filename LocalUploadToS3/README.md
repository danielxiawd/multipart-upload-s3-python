# 本地上传AWS S3，多线程断点续传工具（适合批量的大文件）

从本地硬盘上传批量的大文件到AWS S3存储，例如单个文件1G或500G，特别是Internet网络不稳定的场景，该工具能够完成：
* 大文件的自动分片和断点续传
* 指定单一文件上传
* 目录下的全部文件上传，并跳过太小的文件（小于单个分片的大小）
* 多线程同时上传
* 网络超时自动多次重传，次数可设置。重试采用递增延迟，延迟间隔递增=次数*5秒
* 程序中断，重启启动程序后，程序会查询S3上已完成的分片来进行核对。自动续传未完成的分片，和未完成的文件。完成全部分片传输，在S3上合并前会再次查询和本地数量比对

Version 0.92 说明：该版本修改原来0.9Demo的机制，不拆物理分片，只做索引，不需要再占用临时目录的空间去存放分片。
开发语言改为：Python 3.6   
by James Huang

## AWS 认证配置

You need to set up your AWS security credentials before the sample code is able
to connect to AWS. You can do this by creating a file named "credentials" at ~/.aws/
(`C:\Users\USER_NAME\.aws\` for Windows users) and saving the following lines in the file:

    [default]
    aws_access_key_id = <your access key id>
    aws_secret_access_key = <your secret key>

See the [Security Credentials](http://aws.amazon.com/security-credentials) page

## 应用配置

修改配置 config.py 文件，参数说明:
* srcdir
原文件存放目录
* srcfileIndex
指定要上传的文件的文件名(不含路径)
* chunksize
文件分片大小，不小于5M
* splitdir
分拆文件的临时目录
* s3bucket
S3 bucket名
* s3key
S3 目录前缀 prefix (不含文件名)
* MaxRetry
单个Part上传失败最大重试次数
* MaxThread
同时上传的线程数量
* IgnoreSmallFile
是否跳过小于chunksize的小文件

## 运行应用

程序启动后会对源文件目录下的文件读取，并逐个进行分片和上传 Amazon's [Simple Storage Service (S3)](http://aws.amazon.com/s3),
你需要有一个能上传文件的Bucket

    python multi2s3.py
