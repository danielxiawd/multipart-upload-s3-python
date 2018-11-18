## AWS中国区与海外区S3文件互拷贝，多线程断点续传工具（适合批量的大文件）
* 进入目录 S3CrossRegionToS3

## 本地上传AWS S3，多线程断点续传工具（适合批量的大文件）
* 进入目录 LocalUploadToS3

 以上两个工具现已支持多级目录拷贝，无需本地暂存文件分片或UploadID

## Requirements

该工具需要先安装 `boto3`, the AWS SDK for Python，可以用pip安装

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

## License

This sample application is distributed under the
[Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).