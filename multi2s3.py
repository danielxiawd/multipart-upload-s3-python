# -*- coding: utf-8 -*-
# Python 3.6
# Composed by Huang Zhuobin
# This demo split file into multiparts and use s3 multipart upload to S3 with retry
# 该Demo对大文件进行分拆，多线程进行Multipart上传S3，单个分片传输失败会多次重试，重试次数自定义
# 传输中程序中断了，可以重新运行程序，会自动重传没传成功的Part
# 运行前请配置本机访问AWS S3的KEYID和credential, AWS CLI: aws configure
# 安装boto3 见https://github.com/boto/boto3
# v0.91说明：该版本修改原来0.9Demo的机制，不拆物理分片，只做索引，不需要再占用临时目录的空间去存放分片

import sys
import os
import json
import boto3
from concurrent import futures
from config import srcdir, srcfileIndex, chunksize, splitdir, s3bucket, s3key, MaxRetry, MaxThread, IgnoreSmallFile
from botocore.exceptions import ClientError, EndpointConnectionError
import time
s3client = boto3.client('s3')

# Split file into index parts
def split(srcfile):
    
    partnumber = 1
    fileSize = os.path.getsize(os.path.join(srcdir, srcfile))
    indexList = [0]
    while chunksize * partnumber < fileSize:
        indexList.append(chunksize * partnumber)
        partnumber += 1
    return indexList


# Create multipart upload
def createUpload(srcfile):  
    response = s3client.create_multipart_upload(
        Bucket=s3bucket,
        Key=s3key+srcfile,
    )
    print ("Create_multipart_upload UploadId: ",response["UploadId"])
    uploadIDFilename = os.path.join(splitdir, srcfile + '-uploadID.ini')  
    with open(uploadIDFilename, 'w') as uploadIDfile:
        uploadIDfile.write(response["UploadId"])
    return response["UploadId"]

# Single Thread Upload one part
def uploadThread(uploadId, partnumber, partStartIndex, srcfile, total): 
    print ("Upload part: ",str(partnumber))
    with open(os.path.join(srcdir, srcfile), 'rb') as data:
        retryTime = 0
        while retryTime <= MaxRetry:
            try:
                data.seek(partStartIndex)
                response = s3client.upload_part(
                    Body=data.read(chunksize),
                    Bucket=s3bucket,
                    Key=s3key+srcfile,
                    PartNumber=partnumber,
                    UploadId=uploadId,
                )
                break
            except EndpointConnectionError as e:
                retryTime += 1
                print ("Upload part fail, retry part: ",str(partnumber),"Attempts: ",str(retryTime))
                print ("uploadThreadFunc EndpointConnectionError log: "+str(e))
                if retryTime > MaxRetry:
                    print ("Quit for Max retries: ",str(retryTime))
                    sys.exit()
                time.sleep(5*retryTime)  # 递增延迟重试
            except ClientError as e:
                print ("uploadThreadFunc ClientERR log: ",json.dumps(e.response, default=str))
                sys.exit()
            except Exception as e:
                print ("uploadThreadFunc Exception log: ",str(e))
                sys.exit()
    print ("Uplaod part complete: ",str(partnumber)+"/"+str(total)," Etag: ",response["ETag"])
    return
            

# Recursive upload parts
def uploadPart(uploadId, indexList, partnumberList, srcfile):
    partnumber = 1  # 当前循环要上传的Partnumber
    total = len(indexList)
    # 线程池Start
    with futures.ThreadPoolExecutor(max_workers=MaxThread) as pool:
        for partStartIndex in indexList:
            # start to upload part
            if partnumber not in partnumberList:
                # upload 1 part/thread
                pool.submit(uploadThread, uploadId, partnumber,partStartIndex, srcfile, total) 
            else:
                print ("Part already exist: ",str(partnumber))
            partnumber += 1
    # 线程池End
    print ("All parts uploaded")
    return str(partnumber-1)

# Complete multipart upload
# 通过查询回来的所有Part列表uploadedListParts来构建completeStructJSON
def completeUpload(reponse_uploadId, uploadedListParts, srcfile):  
    # 通过查询回来的所有Part列表uploadedListParts来构建completeStructJSON
    uploadedListPartsClean = []
    for partObject in uploadedListParts:
        ETag = partObject["ETag"]
        PartNumber = partObject["PartNumber"]
        addup = {
            "ETag": ETag,
            "PartNumber": PartNumber
        }
        uploadedListPartsClean.append(addup)
    completeStructJSON = {"Parts": uploadedListPartsClean}

    response = s3client.complete_multipart_upload(
        Bucket=s3bucket,
        Key=s3key+srcfile,
        UploadId=reponse_uploadId,
        MultipartUpload=completeStructJSON  # 重新查询来构建completeStructJSON
    )
    print ("Complete all upload and merged UploadId: ",reponse_uploadId)
    return response

# Print and matching uploaded parts list
# 打印列出已上传的Parts并与本地比对数量
def printPartList(uploadedListParts, indexListLenth):
    print ("Uploaded parts included: ")
    print ("PartNumber       ETag                  LastModified               Size")
    for partObject in uploadedListParts:
        ETag = partObject["ETag"]
        PartNumber = str(partObject["PartNumber"])
        LastModified = str(partObject["LastModified"])
        Size = str(partObject["Size"])
        print (PartNumber,ETag,LastModified,Size)
    uploadedListPartsLenth = len(uploadedListParts)
    if uploadedListPartsLenth == indexListLenth:
        print("Uploaded parts size match.", "\n")
        return ("sizeMatch")
    else:
        print("Warning!!! Uploaded parts size not match as local parts files!", "\n")
        return ("sizeNotMatch")

# Main
if __name__ == '__main__':
    # 分片和索引文件的临时目录，检查不存在则新建
    if not os.path.exists(splitdir):
        os.mkdir(splitdir)

    # 获取源文件目录中所有等待上传文件的列表 srcfileList
    fileListOrg = []
    srcfileList = []
    if srcfileIndex == "*":
        fileListOrg = os.listdir(srcdir)
        for filepath in fileListOrg:
            # 检查文件大小，小于单个分片大小的从列表中去掉（如果IgnoreSmallFile开关打开）
            if (os.path.getsize(os.path.join(srcdir, filepath)) >= chunksize) \
                    or (IgnoreSmallFile == 0):
                srcfileList.append(filepath)
    else:
        srcfileList = [srcfileIndex]

    # 对文件列表srcfileList中的逐个文件进行操作
    for srcfile in srcfileList:
        # 上传文件的UploadID文件
        uploadIDFilename = os.path.join(splitdir, srcfile + '-uploadID.ini')
        # 查看是否曾经建立了上传任务，加载uploadIDFile
        partnumberList = [0]  # 分片Partnumber列表
        try:
            with open(uploadIDFilename, 'r') as uploadIDFile:
                reponse_uploadId = uploadIDFile.read()
            print ("Not the first time to handle: ", srcfile)

            # 有UploadID，则查询S3API 已上传的Partnumber
            try:  # 查询S3API 已上传的Partnumber
                response_uploadedList = s3client.list_parts(
                    Bucket=s3bucket,
                    Key=s3key+srcfile,
                    UploadId=reponse_uploadId,
                )
                #获取已上传的Partnumber List
                if response_uploadedList["NextPartNumberMarker"] > 0:
                    for partnumberObject in response_uploadedList["Parts"]:
                        partnumberList.append(partnumberObject["PartNumber"])
                    print ("Got PartnumberList: ",json.dumps(partnumberList))
                else:
                    print ("No uploaded part")
            except EndpointConnectionError as e:  # 无法连接S3
                print ("Can't connect to S3, check your network")
                print ("log: "+str(e))
                sys.exit()
            except ClientError as e:  # 查不到该UploadID表示该文件已经完成上传并清理
                if e.response['Error']['Code'] == "NoSuchUpload":
                    print ("This is a Finished Upload: ",srcfile)
                    continue  # 下一循环处理下一个文件
                print ("Client log: ",str(e.response['Error']['Code']))
            except Exception as e:
                print ("Exception err, quit because: "+str(e))
                sys.exit()

        except IOError:  # 读不到uploadIDFile，即没启动过上传任务
            print ("First time to handle: ", srcfile)
            # 向S3创建Multipart Upload任务，获取UploadID
            reponse_uploadId = createUpload(srcfile)

        # 获取索引列表
        response_indexList = split(srcfile)
        # 执行分片upload
        response_uploadpart = uploadPart(reponse_uploadId, response_indexList, partnumberList, srcfile)
        print ("Last uploaded partnumber: ",response_uploadpart,"\n")

        # 列出S3上全部已完成的Parts，并与本地比对
        response_uploadedList = s3client.list_parts(
            Bucket=s3bucket,
            Key=s3key+srcfile,
            UploadId=reponse_uploadId,
        )
        compareResult = printPartList(
            response_uploadedList["Parts"], len(response_indexList))
        if compareResult == "sizeNotMatch":
            print("Warning uploaded part sizeNotMatch ERR! Quit")
            sys.exit()

        # 合并S3上的文件
        response_complete = completeUpload(
            reponse_uploadId, response_uploadedList["Parts"], srcfile)
        print ("Finish: ",json.dumps(response_complete["Location"]))

    print ("Complete all files in folder: ",srcdir)



