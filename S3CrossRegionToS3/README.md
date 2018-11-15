# 中国区与海外区互拷贝S3文件，多线程断点续传工具（适合批量的大文件）

从中国区AWS S3拷贝批量的大文件到海外AWS S3存储，例如单个文件1G或500G，同样也可以从海外区拷贝到中国区。
该工具能够完成：
* S3源文件的自动分片获取，并上传到目的S3，断点续传
* 可以指定单一文件拷贝
* 也可以目录下的全部文件拷贝，并跳过太小的文件（小于单个分片的大小）注意：只拷贝指定Bucket和Prefix目录下的文件，不会拷贝下级子目录的内容
* 多线程同时下载和上传
* 网络超时自动多次重传，次数可设置。重试采用递增延迟，延迟间隔递增=次数*5秒
* 程序中断，重启启动程序后，程序会查询S3上已完成的分片来进行核对。自动重传未完成的分片，并完成未完成的文件。完成全部分片传输，在S3上合并前会再次查询和本地数量比对。

Version 0.92
开发语言改为：Python 3.6   
by James Huang

## AWS 认证配置

请在crossS3config.py文件中分别配置中国区和海外区的credential

See the [Security Credentials](http://aws.amazon.com/security-credentials) page

## 应用配置

修改配置 crossS3config.py

## 运行应用

程序启动后会对源文件目录下的文件读取，并逐个进行分片和上传 Amazon's [Simple Storage Service (S3)](http://aws.amazon.com/s3),
你需要在目的S3上有一个有写入权限的Bucket

    python crossS3.py
