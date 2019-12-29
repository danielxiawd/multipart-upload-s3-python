# 中国区与海外区互拷贝S3文件，多线程断点续传工具（适合批量的大文件）

从中国区AWS S3拷贝批量的大文件到海外AWS S3存储，例如单个文件1G或500G，同样也可以从海外区拷贝到中国区。
该工具能够完成：
* S3源文件的自动分片获取，并上传到目的S3，断点续传，每个文件上传完都进行MD5校验
* 多线程同时下载和上传，网络超时自动多次重传，次数可设置。重试采用递增延迟，延迟间隔递增=次数*5秒
* 可以指定单一文件拷贝，也可以目录下的全部文件拷贝，自动遍历下级子目录
* 可设置跳过太小的文件（小于单个分片的大小）
* 程序中断，重启启动程序后，程序会查询S3上已完成的分片来进行核对。自动重传未完成的分片
* 如果某个文件传输到一半，要修改chunksize。请中断，然后在启动时选择Clean unfinished upload，程序会清除未完成文件，并重新上传整个文件
* 注意chunksize的大小设置。S3的Multi_part_upload最大只支持1万个分片

Version 0.94  
* 每个文件上传完都进行MD5校验    
  
Version 0.93c
* 支持设置目的存储的级别 StorageClass
  
Version 0.93b
* 支持多级目录复制；
* 不再依赖本地UploadId的ini文件比对，而是跟目标文件夹比对，有相同文件名和Size则跳过不传；有未完成的Multi_part_upload，则取时间最后的一个就行自动续传
* 查询文件列表、分片列表均可突破原来版本1000的限制。S3单次查询列表最大返回1000，现在做了续查。
* 调用本地~/.aws 配置的 credentials，无需额外配置认证信息

开发语言改为：Python 3.6   
by James Huang

## AWS 认证配置

Create a file named "credentials" at ~/.aws/ (`C:\Users\USER_NAME\.aws\` for Windows users) and saving the following lines in the file:

    [default]
    aws_access_key_id = <your access key id>
    aws_secret_access_key = <your secret key>
Create a file named "config" at ~/.aws/ (`C:\Users\USER_NAME\.aws\` for Windows users) and saving the following lines in the file:

    [default]
    region = <your region>
    output=text

上面 "default" 配置的是 profle name，在本工具中，你需要配置两个 profile ，一个是访问源 S3，一个是访问目的 S3。示例：

在 credentials 文件中：

    [beijing]
    aws_access_key_id=XXXXXXXXXXXXXXX
    aws_secret_access_key=XXXXXXXXXXXXXXXXXXXXXX

    [oregon]
    aws_access_key_id=XXXXXXXXXXXXXXX
    aws_secret_access_key=XXXXXXXXXXXXXXXXXXXXXX

在 config 文件中：

    [profile beijing]
    region=cn-north-1
    output=text

    [profile oregon]
    region=us-west-2
    output=text

See the [Security Credentials](http://aws.amazon.com/security-credentials) page for more detail

## 应用配置

修改配置 S3toS3_config.py

## 运行应用

程序启动后会对源文件目录下的文件读取，并逐个进行分片和上传 Amazon's [Simple Storage Service (S3)](http://aws.amazon.com/s3),
你需要在目的S3上有一个有写入权限的Bucket

    python3 S3toS3.py
