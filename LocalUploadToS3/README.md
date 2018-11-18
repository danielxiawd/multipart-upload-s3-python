# 本地上传AWS S3，多线程断点续传工具（适合批量的大文件）

从本地硬盘上传批量的大文件到AWS S3存储，例如单个文件1G或500G，特别是Internet网络不稳定的场景，该工具能够完成：
* 本地源文件的自动分片获取，并上传到目的S3，断点续传
* 多线程同时下载和上传，网络超时自动多次重传，次数可设置。重试采用递增延迟，延迟间隔递增=次数*5秒
* 可以指定单一文件拷贝，也可以目录下的全部文件拷贝，自动遍历下级子目录
* 可设置跳过太小的文件（小于单个分片的大小）
* 程序中断，重启启动程序后，程序会查询S3上已完成的分片来进行核对。自动重传未完成的分片
* 如果某个文件传输到一半，要修改chunksize。请中断，然后在启动时选择Clean unfinished upload，程序会清除未完成文件，并重新上传整个文件
* 注意chunksize的大小设置。S3的Multi_part_upload最大只支持1万个分片

Version 0.93
* 支持多级目录复制；
* 不再依赖本地UploadId的ini文件比对，而是跟目标文件夹比对，有相同文件名和Size则跳过不传；有未完成的Multi_part_upload，则取时间最后的一个就行自动续传
* 查询文件列表、分片列表均可突破原来版本1000的限制。S3单次查询列表最大返回1000，现在做了续查。 
Version 0.92 
* 该版本修改原来0.9Demo的机制，不拆物理分片，只做索引，不需要再占用临时目录的空间去存放分片。

开发语言改为：Python 3.6   
by James Huang

## AWS 认证配置

请在local2S3_config.py文件中配置S3的credential

See the [Security Credentials](http://aws.amazon.com/security-credentials) page

## 应用配置

修改配置 local2s3_config.py

## 运行应用

程序启动后会对源文件目录下的文件读取，并逐个进行分片和上传 Amazon's [Simple Storage Service (S3)](http://aws.amazon.com/s3),
你需要有一个能上传文件的Bucket

    python3 local2s3.py
