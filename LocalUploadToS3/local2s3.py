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
from local2s3_config import srcdir, srcfileIndex, chunksize, desBucket, srcPrefix, MaxRetry, MaxThread, IgnoreSmallFile, desRegion, des_aws_access_key_id, des_aws_secret_access_key
from botocore.exceptions import ClientError, EndpointConnectionError
import time
s3DESclient = boto3.client(
    's3',
    aws_access_key_id=des_aws_access_key_id,
    aws_secret_access_key=des_aws_secret_access_key,
    region_name=desRegion)
if srcdir[-1]=='/':
    srcdir = srcdir[:len(srcdir)-1]

# Split file into index parts
def split(srcfile):
    partnumber = 1
    indexList = [0]
    while chunksize * partnumber < srcfile["Size"]:
        indexList.append(chunksize * partnumber)
        partnumber += 1
    if partnumber > 10000:
        print(f'\nPART NUMBER LIMIT 10,000. YOUR FILE HAS {partnumber}. ')
        print('PLEASE CHANGE THE chunksize IN CONFIG FILE AND TRY AGAIN')
        os._exit(0)
    return indexList


# Create multipart upload
def createUpload(srcfile):
    response = s3DESclient.create_multipart_upload(
        Bucket=desBucket,
        Key=os.path.join(srcPrefix, srcfile["Key"]),
    )
    print ("Create_multipart_upload UploadId: ",response["UploadId"])
    return response["UploadId"]

# Single Thread Upload one part
def uploadThread(uploadId, partnumber, partStartIndex, srcfileKey, total):
    print(f'Uploading {partnumber}/{total} ...')
    with open(os.path.join(srcdir, srcfileKey), 'rb') as data:
        retryTime = 0
        while retryTime <= MaxRetry:
            try:
                data.seek(partStartIndex)
                s3DESclient.upload_part(
                    Body=data.read(chunksize),
                    Bucket=desBucket,
                    Key=os.path.join(srcPrefix, srcfileKey),
                    PartNumber=partnumber,
                    UploadId=uploadId,
                )
                break
            except Exception as e:
                retryTime += 1
                print ("uploadThreadFunc log:",str(e))
                print ("Upload part fail, retry part:",str(partnumber),"Attempts: ",str(retryTime))
                if retryTime > MaxRetry:
                    print ("Quit for Max retries: ",str(retryTime))
                    os._exit(0)
                time.sleep(5*retryTime)  # 递增延迟重试
    print(f'               Complete {partnumber}/{total}','% .2f % %'% (partnumber/total*100))
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
                pool.submit(uploadThread, uploadId, partnumber, partStartIndex, srcfile["Key"], total)
            partnumber += 1
    # 线程池End
    print(f'All parts uploaded, size: {srcfile["Size"]}')
    return str(partnumber-1)

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
            Key=os.path.join(srcPrefix, srcfileKey),
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
        print ("Uploaded parts size not match")
        os._exit(0)
    completeStructJSON = {"Parts": uploadedListPartsClean}

    # S3合并multipart upload任务
    response = s3DESclient.complete_multipart_upload(
        Bucket=desBucket,
        Key=os.path.join(srcPrefix, srcfileKey),
        UploadId=reponse_uploadId,
        MultipartUpload=completeStructJSON  
    )
    print ("Complete all upload and merged UploadId: ",reponse_uploadId)
    return response


# 查询S3API 已上传的Partnumber
def checkPartnumberList(srcfile, reponse_uploadId):
    try:  
        partnumberList = []
        PartNumberMarker = 0
        IsTruncated = True
        while IsTruncated == True:
            response_uploadedList = s3DESclient.list_parts(
                Bucket=desBucket,
                Key=os.path.join(srcPrefix, srcfile["Key"]),
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
        if partnumberList != []:  # 如果为0则表示没有查到已上传的Part
            print("Got partnumber list: ", partnumberList)
    except Exception as e:
        print("Exception err, quit \n"+str(e))
        os._exit(0)
    return partnumberList

# 获取目标文件列表，含Key和文件Size
def getDESFileList():
    fileList = []
    response_fileList = s3DESclient.list_objects_v2(
        Bucket=desBucket,
        Prefix=srcPrefix,
        MaxKeys=1000
    )
    for n in response_fileList["Contents"]:
        if n["Key"][-1] != '/':      # Key以"/“结尾的是子目录，不处理
            fileList.append({
                "Key": n["Key"],
                "Size": n["Size"]
            })
    while response_fileList["IsTruncated"]:
        response_fileList = s3DESclient.list_objects_v2(
            Bucket=desBucket,
            Prefix=srcPrefix,
            MaxKeys=1000,
            ContinuationToken=response_fileList["NextContinuationToken"]
        )
        for n in response_fileList["Contents"]:
            if n["Key"][-1] != '/':      # Key以"/“结尾的是子目录，不处理
                fileList.append({
                    "Key": n["Key"],
                    "Size": n["Size"]
                })
    return fileList
    
# 获取Bucket/Prefix中所有未完成的Multipart Upload
def getUploadIdList():
    NextKeyMarker=''
    IsTruncated = True
    UploadIdList=[]
    while IsTruncated:
        response = s3DESclient.list_multipart_uploads(
            Bucket=desBucket,
            Prefix=srcPrefix,
            MaxUploads=1000,
            KeyMarker=NextKeyMarker
        )
        IsTruncated = response["IsTruncated"]
        NextKeyMarker = response["NextKeyMarker"]
        if NextKeyMarker != '':
            for n in response["Uploads"]:
                UploadIdList.append({
                    "Key": n["Key"],
                    "Initiated": n["Initiated"],
                    "UploadId": n["UploadId"]
                })
                print(f'Unfinished upload: Key: {n["Key"]}, Time: {n["Initiated"]}')
    return UploadIdList

# 查找Key是否存在，并且Size一致
def checkFileExist(srcfile, desFilelist, UploadIdList):
    # 检查源文件是否在目标文件夹中
    for f in desFilelist:
        if f["Key"] == os.path.join(srcPrefix,srcfile["Key"]) and \
            (srcfile["Size"] == f["Size"]):  
            return 'NEXT'  # 文件完全相同
    # 找不到文件，或文件不一致，要重新传的
    # 查Key是否有未完成的UploadID
    keyIDList=[]
    for u in UploadIdList:
        if u["Key"] == os.path.join(srcPrefix, srcfile["Key"]):
            keyIDList.append(u)
    # 如果找不到上传过的Upload，则从头开始传
    if keyIDList == []:
        return 'UPLOAD'
    # 对同一个Key（文件）的不同Upload找出时间最晚的值
    UploadID_latest = keyIDList[0]
    for u in keyIDList:
        if u["Initiated"] > UploadID_latest["Initiated"]:
            UploadID_latest = u
    return UploadID_latest["UploadId"]

# Main
if __name__ == '__main__':
    # 检查目标S3能否写入
    s3DESclient.put_object(
        Bucket=desBucket,
        Key=os.path.join(srcPrefix, 'access_test'),
        Body='access_test_content'
    )

    # 获取源文件目录中所有等待上传文件的列表 srcfileList
    srcfileList = []
    if srcfileIndex == "*":
        for parent, dirnames, filenames in os.walk(srcdir):
            for filename in filenames:  # 遍历输出文件信息
                file_absPath = os.path.join(parent, filename)
                file_relativePath = file_absPath[len(srcdir)+1:]
                file_size = os.path.getsize(file_absPath)
                if (file_size >= chunksize) or (IgnoreSmallFile == 0):
                    srcfileList.append({
                        "Key": file_relativePath,
                        "Size": file_size
                    })
    else:
        srcfileList = [srcfileIndex]
    # 获取目标文件夹现存文件列表
    desFilelist = getDESFileList()
    # 获取Bucket/Prefix中所有未完成的Multipart Upload
    UploadIdList = getUploadIdList()

    # 是否清理所有未完成的Multipart Upload, 用于强制重传
    if UploadIdList != []:
        print(f'There are {len(UploadIdList)} unfinished upload, do you want to clean them and restart?')
        print('NOTICE: IF CLEAN, YOU CANNOT RESUME ANY UNFINISHED UPLOAD')
        keyboard_input = input("CLEAN? Please confirm: (n/CLEAN)")
        if keyboard_input == 'CLEAN':
            # 清理所有未完成的Upload
            for n in UploadIdList:
                response = s3DESclient.abort_multipart_upload(
                    Bucket=desBucket,
                    Key=n["Key"],
                    UploadId=n["UploadId"]
                )
            UploadIdList=[]
            print('CLEAN FINISHED')
        else:
            print('Do not clean, keep the unfinished upload')

    # 对文件列表srcfileList中的逐个文件进行操作
    for srcfile in srcfileList:
        print('')
        # 检查文件是否已存在，存在不继续、不存在且没UploadID要新建、不存在但有UploadID得到返回的UploadID
        response_check_upload=checkFileExist(srcfile, desFilelist, UploadIdList)
        if response_check_upload == 'UPLOAD':
            reponse_uploadId = createUpload(srcfile)
            print(f'For new upload: {srcfile["Key"]}')
            partnumberList=[]
        elif response_check_upload == 'NEXT':
            print(f'Duplicated. {srcfile["Key"]} already exist, and same size. Handle next file.')
            continue
        else:
            reponse_uploadId=response_check_upload
            # 获取已上传partnumberList
            partnumberList = checkPartnumberList(srcfile, reponse_uploadId)

        # 获取索引列表
        response_indexList = split(srcfile)
        # 执行分片upload
        response_uploadpart = uploadPart(reponse_uploadId, response_indexList, partnumberList, srcfile)

        # 合并S3上的文件
        response_complete = completeUpload(
            reponse_uploadId, srcfile["Key"], len(response_indexList))
        print(f'FINISH: {srcfile} UPLOADED TO {response_complete["Location"]}\n')
    print(f'Complete all files in folder: {srcdir} TO {desBucket}/{srcPrefix}')
