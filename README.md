# AWS S3 多线程断点续传工具 v1.0  
适合批量的大文件断点续传到 AWS S3  
MulitiTread S3 upload tools, Breakpoint resume supported, suitable for large files  

从本地硬盘上传，或海外与中国区 AWS S3 存储之间互相拷贝，例如单个文件1G或500G。支持多级目录拷贝，具体功能包括：  
* 本地或S3源文件的自动分片获取，并上传到目的S3，断点续传，每个分片以及每个文件上传完都进行MD5校验
* 多文件多线程同时下载和上传，网络超时自动多次重传，次数可设置。重试采用递增延迟，延迟间隔递增=次数*5秒
* 可以指定单一文件拷贝，也可以目录下的全部文件拷贝，自动遍历下级子目录
* 可设置跳过太小的文件（小于单个分片的大小）
* 程序中断，重启启动程序后，程序会查询S3上已完成的分片来进行核对。自动重传未完成的分片
* 如果某个文件传输到一半，要修改chunksize。请中断，然后在启动时选择Clean unfinished upload，程序会清除未完成文件，并重新上传整个文件  
  
* 注意 chunksize 的大小设置。S3的Multi_part_upload最大只支持1万个分片

开发语言：Python 3.7   
by James Huang  

## AWS 认证配置
 
创建文件名为 `"credentials"` 于 ~/.aws/ 目录(`C:\Users\USER_NAME\.aws\` for Windows users) 并保存以下内容:

    [default]
    region = <your region>
    aws_access_key_id = <your access key id>
    aws_secret_access_key = <your secret key>

上面 "default" 是默认 profle name，如果是S3 copy to S3你需要配置两个 profile ，一个是访问源 S3，一个是访问目的 S3。示例：

例如在 credentials 文件中：

    [beijing]
    region=cn-north-1
    aws_access_key_id=XXXXXXXXXXXXXXX
    aws_secret_access_key=XXXXXXXXXXXXXXXXXXXXXX

    [oregon]
    region=us-west-2
    aws_access_key_id=XXXXXXXXXXXXXXX
    aws_secret_access_key=XXXXXXXXXXXXXXXXXXXXXX

See the [Security Credentials](http://aws.amazon.com/security-credentials) page for more detail

## 应用配置

修改配置 `s3_upload_config.py`
上面配置的 profile name 填入对应源和目的 profile name 项

## 运行应用

程序启动后会对源文件目录下的文件读取，并逐个进行分片和上传，你需要有一个能上传文件的Bucket

    python3 s3_upload.py

## Requirements

该工具需要先安装 `boto3`, the AWS SDK for Python，可以用 pip 安装

    pip install boto3

详见 [boto3](https://github.com/boto/boto3) github page
for more information on getting your keys. For more information on configuring `boto3`,
check out the Quickstart section in the [developer guide](https://boto3.readthedocs.org/en/latest/guide/quickstart.html).

You need to make sure the credentials you're using have the correct permissions to access the Amazon S3
service. If you run into 'Access Denied' errors while running this sample, please follow the steps below.

1. Log into the [AWS IAM Console](https://console.aws.amazon.com/iam/home)
2. Navigate to the Users page.
3. Find the AWS IAM user whose credentials you're using.
4. Under the 'Permissions' section, attach the policy called 'AmazonS3FullAccess'
5. Re-run the application. Now your user should have the right permissions to run the sample.

Please be aware of the [restrictions for bucket names](http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html) when you start creating your own buckets.

## 配置文件示例 S3 copy to S3
```
"""Basic Configure"""
JobType = "S3_TO_S3"  # 'LOCAL_TO_S3' | 'S3_TO_S3'
SrcFileIndex = "*"  # 指定要上传的文件的文件名, type = str，Upload全部文件则用 "*"
S3Prefix = "multipart/"  # S3_TO_S3源S3的Prefix，LOCAL_TO_S3则为目标S3的Prefix, type = str
DesProfileName = "cn"  # 在~/.aws 中配置的能访问目标S3的 profile name
DesBucket = "my-cn-bucket"  # 目标文件bucket, type = str

"""Configure for LOCAL_TO_S3"""
SrcDir = "no_used"
# 原文件本地存放目录, S3_TO_S3则该字段无效 type = str

"""Configure for S3_TO_S3"""
SrcBucket = "my-us-bucket"  # 源Bucket，LOCAL_TO_S3则本字段无效
SrcProfileName = "us"  # 在~/.aws 中配置的能访问源S3的 profile name，LOCAL_TO_S3则本字段无效

"""Advanced Configure"""
Megabytes = 1024*1024
ChunkSize = 50 * Megabytes  # 文件分片大小，不小于5M，单文件分片总数不能超过10000, type = int
MaxRetry = 30  # 单个Part上传失败后，最大重试次数, type = int
MaxThread = 3  # 单文件同时上传的进程数量, type = int
MaxParallelFile = 3  # 并行操作文件数量, type = int
# 即同时并发的进程数 = MaxParallelFile * MaxThread
IgnoreSmallFile = False  # 是否跳过小于chunksize的小文件, type = bool
StorageClass = "STANDARD"
# 'STANDARD'|'REDUCED_REDUNDANCY'|'STANDARD_IA'|'ONEZONE_IA'|'INTELLIGENT_TIERING'|'GLACIER'|'DEEP_ARCHIVE'
ifVerifyMD5 = False
# 整个文件完成上传合并之后再次进行整个文件的ETag校验MD5。该开关不影响每个分片上传时候的MD5校验。
# 对于S3_TO_S3，该开关True会在断点续传的时候重新下载所有已传过的分片来计算MD5
DontAskMeToClean = False  # False 遇到存在现有的未完成upload时，不再询问是否Clean，默认不Clean，自动续传
LoggingLevel = "INFO"  # 日志输出级别 'WARNING' | 'INFO' | 'DEBUG'
```
## 配置文件示例 local copy to S3
```
"""Basic Configure"""
JobType = "LOCAL_TO_S3"  # 'LOCAL_TO_S3' | 'S3_TO_S3'
SrcFileIndex = "*"  # 指定要上传的文件的文件名, type = str，Upload全部文件则用 "*"
S3Prefix = "multipart/"  # S3_TO_S3源S3的Prefix，LOCAL_TO_S3则为目标S3的Prefix, type = str
DesProfileName = "us"  # 在~/.aws 中配置的能访问目标S3的 profile name
DesBucket = "my-us-bucket"  # 目标文件bucket, type = str

"""Configure for LOCAL_TO_S3"""
SrcDir = "/Users/huangzb/Downloads/"
# 原文件本地存放目录, S3_TO_S3则该字段无效 type = str

"""Configure for S3_TO_S3"""
SrcBucket = "no"  # 源Bucket，LOCAL_TO_S3则本字段无效
SrcProfileName = "no"  # 在~/.aws 中配置的能访问源S3的 profile name，LOCAL_TO_S3则本字段无效

"""Advanced Configure"""
Megabytes = 1024*1024
ChunkSize = 50 * Megabytes  # 文件分片大小，不小于5M，单文件分片总数不能超过10000, type = int
MaxRetry = 30  # 单个Part上传失败后，最大重试次数, type = int
MaxThread = 3  # 单文件同时上传的进程数量, type = int
MaxParallelFile = 3  # 并行操作文件数量, type = int
# 即同时并发的进程数 = MaxParallelFile * MaxThread
IgnoreSmallFile = False  # 是否跳过小于chunksize的小文件, type = bool
StorageClass = "STANDARD"
# 'STANDARD'|'REDUCED_REDUNDANCY'|'STANDARD_IA'|'ONEZONE_IA'|'INTELLIGENT_TIERING'|'GLACIER'|'DEEP_ARCHIVE'
ifVerifyMD5 = False
# 整个文件完成上传合并之后再次进行整个文件的ETag校验MD5。该开关不影响每个分片上传时候的MD5校验。
# 对于S3_TO_S3，该开关True会在断点续传的时候重新下载所有已传过的分片来计算MD5
DontAskMeToClean = False  # False 遇到存在现有的未完成upload时，不再询问是否Clean，默认不Clean，自动续传
LoggingLevel = "INFO"  # 日志输出级别 'WARNING' | 'INFO' | 'DEBUG'
```

## License

This sample application is distributed under the
[Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
