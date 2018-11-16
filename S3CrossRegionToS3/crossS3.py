# -*- coding: utf-8 -*-
# Python 3.6
# Composed by Huang Zhuobin
# Cross copy object between China region AWS S3 and Global region AWS S3
# 对S3上的大文件进行分拆分片Part，上传到另一区域的S3上，例如源文件在AWS北京区S3，目标为AWS俄勒冈区域S3
# 多线程操作。传输中程序中断了，可以重新运行程序，会自动重传没传成功的分片

import sys
import os
import json
import boto3
import re
from concurrent import futures
from botocore.exceptions import ClientError, EndpointConnectionError
import time
from crossS3config import srcRegion, srcBucket, srcPrefix, srcfileIndex, src_aws_access_key_id, \
    src_aws_secret_access_key, chunksize, uploadIDdir, MaxRetry, MaxThread, IgnoreSmallFile, \
    desRegion, desBucket, des_aws_access_key_id, des_aws_secret_access_key

s3SRCclient = boto3.client(
    's3',
    aws_access_key_id=src_aws_access_key_id,
    aws_secret_access_key=src_aws_secret_access_key,
    region_name=srcRegion)

s3DESclient = boto3.client(
    's3',
    aws_access_key_id=des_aws_access_key_id,
    aws_secret_access_key=des_aws_secret_access_key,
    region_name=desRegion)

# Split file into index parts
def split(srcfile):
    partnumber = 1
    indexList = [0]
    while chunksize * partnumber < srcfile["Size"]:
        indexList.append(chunksize * partnumber)
        partnumber += 1
    if partnumber > 10000:
        print("Max part number is 10000, but you have:",
              partnumber, ". Please change the chunksize in config file and try again.")
        os._exit(0)
    return indexList

# Create multipart upload
def createUpload(srcfile, uploadIDFilename):
    response = s3DESclient.create_multipart_upload(
        Bucket=desBucket,
        Key=srcfile["Key"],
    )
    print ("Create_multipart_upload UploadId: ",response["UploadId"])
    with open(uploadIDFilename, 'w') as uploadIDfile:
        uploadIDfile.write(response["UploadId"])
    return response["UploadId"]

# Single Thread Upload one part
def uploadThread(uploadId, partnumber, partStartIndex, srcfileKey, total):
    print("Start getting part: ", str(partnumber)+"/" +
          str(total), "...")
    # 下载文件
    retryTime = 0
    while retryTime <= MaxRetry:
        try:
            response_get_object = s3SRCclient.get_object(
                Bucket=srcBucket,
                Key=srcfileKey,
                Range="bytes="+str(partStartIndex)+"-"+str(partStartIndex+chunksize-1)
                )
            getBody = response_get_object["Body"].read()
            break
        except Exception as e:
            retryTime += 1
            print("DownloadThreadFunc Exception log: ", str(e))
            print ("Download part fail, retry part: ",str(partnumber),"Attempts: ",str(retryTime))
            if retryTime > MaxRetry:
                print("Quit for Max Download retries: ",str(retryTime))
                os._exit(0)
            time.sleep(5*retryTime)  # 递增延迟重试

    print("Complete download part: ", str(partnumber)+"/" +
          str(total), ", start to upload ...")
    # 上传文件
    retryTime = 0
    while retryTime <= MaxRetry:
        try:
            response_upload = s3DESclient.upload_part(
                Body=getBody,
                Bucket=desBucket,
                Key=srcfileKey,
                PartNumber=partnumber,
                UploadId=uploadId,
            )
            break
        except Exception as e:
            retryTime += 1
            print("UploadThreadFunc Exception log: ", str(e))
            print ("Upload part fail, retry part: ",str(partnumber),"Attempts: ",str(retryTime))
            if retryTime > MaxRetry:
                print("Quit for Max Upload retries: ",str(retryTime))
                os._exit(0)
            time.sleep(5*retryTime)  # 递增延迟重试

    print("Uplaod part complete: ", str(partnumber)+"/" +
          str(total), " Etag: ", response_upload["ETag"])
    return "Uploaded"

# Recursive upload parts
def uploadPart(uploadId, indexList, partnumberList, srcfileKey):
    partnumber = 1  # 当前循环要上传的Partnumber
    total = len(indexList)
    # 线程池Start
    with futures.ThreadPoolExecutor(max_workers=MaxThread) as pool:
        for partStartIndex in indexList:
            # start to upload part
            if partnumber not in partnumberList:
                # upload 1 part/thread
                pool.submit(uploadThread, uploadId, partnumber, partStartIndex, srcfileKey, total)
            else:
                print("Part already exist: ", str(partnumber))
            partnumber += 1
    # 线程池End
    print("All parts uploaded")
    return str(partnumber-1)

# Print and matching uploaded parts list
# 打印列出已上传的Parts并与本地比对数量
def printPartList(uploadedListParts, indexListLenth):
    print("Uploaded parts included: ")
    print("PartNumber       ETag                  LastModified               Size")
    for partObject in uploadedListParts:
        ETag = partObject["ETag"]
        PartNumber = str(partObject["PartNumber"])
        LastModified = str(partObject["LastModified"])
        Size = str(partObject["Size"])
        print(PartNumber, ETag, LastModified, Size)
    uploadedListPartsLenth = len(uploadedListParts)
    if uploadedListPartsLenth == indexListLenth:
        print("Uploaded parts size match.", "\n")
        return ("sizeMatch")
    else:
        print("Warning!!! Uploaded parts size not match as local parts files!", "\n")
        return ("sizeNotMatch")

# Complete multipart upload
# 通过查询回来的所有Part列表uploadedListParts来构建completeStructJSON
def completeUpload(reponse_uploadId, srcfileKey, len_indexList):
    # 查询S3的所有Part列表uploadedListParts构建completeStructJSON
    uploadedListPartsClean = []
    PartNumberMarker = 0
    IsTruncated = True
    while IsTruncated == True:
        response_uploadedList = s3DESclient.list_parts(
            Bucket=desBucket,
            Key=srcfileKey,
            UploadId=reponse_uploadId,
            MaxParts=1000,
            PartNumberMarker=PartNumberMarker
        )
        NextPartNumberMarker = response_uploadedList['NextPartNumberMarker']
        IsTruncated = response_uploadedList['IsTruncated']
        if NextPartNumberMarker > 0:
            for partObject in response_uploadedList["Parts"]:
                ETag = partObject["ETag"]
                PartNumber = partObject["PartNumber"]
                addup = {
                    "ETag": ETag,
                    "PartNumber": PartNumber
                }
                uploadedListPartsClean.append(addup)
        PartNumberMarker = NextPartNumberMarker
    if len(uploadedListPartsClean) != len_indexList:
        print("Uploaded parts size not match")
        os._exit(0)
    completeStructJSON = {"Parts": uploadedListPartsClean}

    # S3合并multipart upload任务
    response = s3DESclient.complete_multipart_upload(
        Bucket=desBucket,
        Key=srcfileKey,
        UploadId=reponse_uploadId,
        MultipartUpload=completeStructJSON
    )
    print("Complete all upload and merged UploadId: ", reponse_uploadId)
    return response

# 查询S3API 已上传的Partnumber
def checkPartnumberList(srcfile, reponse_uploadId):
    try:
        partnumberList = [0]
        PartNumberMarker = 0
        IsTruncated = True
        while IsTruncated == True:
            response_uploadedList = s3DESclient.list_parts(
                Bucket=desBucket,
                Key=srcfile["Key"],
                UploadId=reponse_uploadId,
                MaxParts=1000,
                PartNumberMarker=PartNumberMarker
            )
            NextPartNumberMarker = response_uploadedList['NextPartNumberMarker']
            IsTruncated = response_uploadedList['IsTruncated']
            if NextPartNumberMarker > 0:
                for partnumberObject in response_uploadedList["Parts"]:
                    partnumberList.append(partnumberObject["PartNumber"])
            PartNumberMarker = NextPartNumberMarker
        if partnumberList != [0]:  # 如果为0则表示没有查到已上传的Part
            print("Got partnumber list: ", partnumberList)

    except EndpointConnectionError as e:  # 无法连接S3
        print("Can't connect to S3, check your network")
        print("log: "+str(e))
        sys.exit()
    except ClientError as e:  # 查不到该UploadID表示该文件已经完成上传并清理
        if e.response['Error']['Code'] == "NoSuchUpload":
            print("This is a Finished Upload: ", srcfile)
            return []  # 传递Nulll回去，表示跳下一循环处理下一个大文件
        print("Client log: ", str(e.response['Error']['Code']))
    except Exception as e:
        print("Exception err, quit because: "+str(e))
        os._exit(0)
    return partnumberList

# Main
if __name__ == '__main__':
    # 索引文件的临时目录，检查不存在则新建
    if not os.path.exists(uploadIDdir):
        os.mkdir(uploadIDdir)

    # 检查目标S3能否写入
    s3DESclient.put_object(
        Bucket=desBucket,
        Key=srcPrefix+'access_test',
        Body='access_test_content'
    )

    # 获取文件列表，含Key和文件Size
    fileList = []
    # 原文件名为*则查文件列表，否则就查单个文件
    if srcfileIndex == "*":
        response_fileList = s3SRCclient.list_objects(
            Bucket=srcBucket,
            Prefix=srcPrefix,
        )
        for n in response_fileList["Contents"]:
            # 检查文件大小，小于单个分片大小的从列表中去掉（如果IgnoreSmallFile开关打开）
            if (n["Size"] >= chunksize) or (IgnoreSmallFile == 0):
                fileList.append({
                    "Key": n["Key"],
                    "Size": n["Size"]
                })
    else:
        response_fileList = s3SRCclient.head_object(
            Bucket=srcBucket,
            Key=srcPrefix+srcfileIndex
        )
        fileList = [{
            "Key": srcPrefix+srcfileIndex,
            "Size": response_fileList["ContentLength"]
        }]

    # 对文件列表fileList中的逐个文件进行操作
    for srcfile in fileList:
        # 保存上传UploadID的文件，把文件子目录"/"替换为"-"作为文件名
        pattern = re.compile('/')
        uploadIDFilename_sub = re.sub(pattern, '-', srcfile["Key"])
        uploadIDFilename = os.path.abspath(os.path.join(
            uploadIDdir, uploadIDFilename_sub + '.ini'))
        # 查看是否曾经建立了上传任务，加载uploadIDFile
        try:
            partnumberList = [0]  # 分片Partnumber列表
            with open(uploadIDFilename, 'r') as uploadIDFile:
                reponse_uploadId = uploadIDFile.read()
            print("Not the first time to handle: ", srcfile["Key"])

            # 有UploadID，则查询S3API 已上传的Partnumber
            partnumberList = checkPartnumberList(srcfile, reponse_uploadId)
            if partnumberList == []:
                continue  # 下一循环处理下一个文件

        except IOError:  # 读不到uploadIDFile，即没启动过上传任务
            print("First time to handle: ", srcfile["Key"])
            # 向S3创建Multipart Upload任务，获取UploadID
            reponse_uploadId = createUpload(srcfile, uploadIDFilename)

        # 获取索引列表
        response_indexList = split(srcfile)

        # 执行分片upload
        response_uploadpart = uploadPart(reponse_uploadId, response_indexList, partnumberList, srcfile["Key"])
        print ("Last uploaded partnumber: ",response_uploadpart,"\n")

        # 合并S3上的文件
        response_complete = completeUpload(
            reponse_uploadId, srcfile["Key"], len(response_indexList))
        print("Finish: ", json.dumps(response_complete["Location"]))

    print("Copy mission accomplished, FROM (Region/Bucket/Prefix): ",
          srcRegion+"/"+srcBucket+"/"+srcPrefix, " TO ", desRegion+"/"+desBucket+"/"+srcPrefix)
