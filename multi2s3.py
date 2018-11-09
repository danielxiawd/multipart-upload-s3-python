# -*- coding: utf-8 -*-
# Python 2.7
# Composed by Huang Zhuobin
# This demo split file into multiparts and use s3 multipart upload to S3 with retry
# 该Demo对大文件进行分拆，多线程进行Multipart上传S3，单个分片传输失败会多次重试，重试次数自定义
# 传输中程序中断了，可以重新运行程序，会自动重传没传成功的Part
# 运行前请配置本机访问AWS S3的KEYID和credential, AWS CLI: aws configure
# 安装boto3 见https://github.com/boto/boto3

import sys
import os
import json
import boto3
from concurrent import futures
from config import srcdir, srcfileIndex, chunksize, splitdir, s3bucket, s3key, MaxRetry, MaxThread, MaunalMerge, IgnoreSmallFile
from botocore.exceptions import ClientError, EndpointConnectionError
import time
s3client = boto3.client('s3')

def split(srcfile):  # Split file into parts
    indexFilename = os.path.join(splitdir, srcfile + '-indexfile.json')  # 1个文件所有分片的索引文件
    partnumber =0
    inputfile = open(os.path.join(srcdir, srcfile), 'rb')
    indexList = []
    while True:
        chunk = inputfile.read(chunksize)
        if not chunk:
            break
        partnumber += 1
        partFileName = os.path.join(splitdir, srcfile+'-part%04d' % partnumber)
        print "Split part filename: "+partFileName
        try:
            fileobj = open(partFileName, 'wb')  # make partfile
            fileobj.write(chunk)  # write data into partfile
            fileobj.close()
            print "write to part file complete: "+partFileName
        except IOError as e:
            print "Can't write to disk: "+partFileName
            sys.exit()
        except Exception as e:
            print str(e)
            sys.exit()
        indexList.append(partFileName)
    inputfile.close()

    # write to index file
    indexfile = open(indexFilename, 'w')
    indexfile.write(json.dumps(indexList))
    indexfile.close()
    print ""
    print "Complete split, please view for detail: "+indexFilename
    print ""
    return indexList

def createUpload(srcfile): # create multipart upload
    response = s3client.create_multipart_upload(
        Bucket=s3bucket,
        Key=s3key+srcfile,
    )
    print "Create_multipart_upload UploadId: "+response["UploadId"]
    print ""
    uploadIDFilename = os.path.join(splitdir, srcfile + '-uploadID.ini') # 1个文件的UploadID文件
    uploadIDfile = open(uploadIDFilename, 'w')
    uploadIDfile.write(response["UploadId"])
    uploadIDfile.close()
    return response["UploadId"]

def uploadThread(uploadId, partnumber, partFileName, srcfile): # 单个Part上传开始
    print "Start to upload partFile: "+str(partnumber)+"\n"
    with open(os.path.abspath(partFileName), 'rb') as data:
        retryTime = 0
        while retryTime <= MaxRetry:
            try:
                response = s3client.upload_part(
                    Body=data,
                    Bucket=s3bucket,
                    Key=s3key+srcfile,
                    PartNumber=partnumber,
                    UploadId=uploadId,
                )
                break
            except EndpointConnectionError as e:
                retryTime += 1
                print "Upload part fail, retry part: " + \
                    str(partnumber)+" RetryAttempts: "+str(retryTime)
                print "uploadThreadFunc EndpointConnectionError log: "+str(e)
                if retryTime > MaxRetry:
                    print "Quit for Max retries: "+str(retryTime)
                    sys.exit()
                time.sleep(5*retryTime) # 递增延迟重试
            except ClientError as e:
                print "uploadThreadFunc ClientERR log: "+json.dumps(e.response, default=str)
                sys.exit()
            except Exception as e:
                print "uploadThreadFunc Exception log: "+str(e)
                sys.exit()
    print "Uplaod part complete: " + str(partnumber)+" Etag: "+response["ETag"]

def uploadPart(uploadId, indexList, partnumberList, srcfile): # recursive upload parts
    partnumber = 1 # 当前循环要上传的Partnumber
    # 线程池Start
    with futures.ThreadPoolExecutor(max_workers=MaxThread) as pool:
        for partFileName in indexList: 
            # start to upload part
            if partnumber not in partnumberList:
                pool.submit(uploadThread, uploadId, partnumber, partFileName, srcfile)  # upload 1 part/thread
            else:
                print "Part already exist: "+str(partnumber)
            partnumber += 1
    # 线程池End
    print "All parts uploaded"
    return str(partnumber-1)

def completeUpload(reponse_uploadId, uploadedListParts, srcfile): # complete multipart upload
    # 通过查询回来的所有Part列表uploadedListParts来构建completeStructJSON
    uploadedListPartsClean =[]
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
    print "Complete all upload and merged UploadId: "+reponse_uploadId
    print ""
    return response

def printPartList(uploadedListParts): # 打印列出已上传的Parts
    print "Uploaded parts included: "
    print "PartNumber       ETag                  LastModified               Size"
    for partObject in uploadedListParts:
        ETag = partObject["ETag"]
        PartNumber = str(partObject["PartNumber"])
        LastModified = str(partObject["LastModified"])
        Size = str(partObject["Size"])
        print PartNumber+"  "+ETag+"  "+LastModified+"  "+Size
    print ""
    print ""

def cleanParts(indexList): # 清理临时分片
    for cleanid in indexList:
        try:
            os.remove(cleanid)
        except Exception as e:
            print "CleanPartsFunc err log: "+str(e)

if __name__=='__main__':
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
        try:
            partnumberList = [0] # 分片Partnumber列表
            uploadIDFile = open(uploadIDFilename, 'r')
            reponse_uploadId = uploadIDFile.read()
            uploadIDFile.close()
            print "Not the first time to handle: "+srcfile
            print "Getting S3 part list..."
            # 有UploadID，则查询S3API 已上传的Partnumber,
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
                    print "Got PartnumberList: "+json.dumps(partnumberList)
                else:
                    print "No uploaded part"
            except EndpointConnectionError as e: # 无法连接S3
                print "Can't connect to S3, check your network"
                print "log: "+str(e)
                sys.exit()
            except ClientError as e: # 查不到该UploadID表示该文件已经完成上传并清理
                if e.response['Error']['Code'] == "NoSuchUpload":
                    print "This is a Finished Upload: "+srcfile
                    continue # 下一循环处理下一个文件
                print "Client log: "+str(e.response['Error']['Code'])
            except Exception as e:
                print "Exception err, quit because: "+str(e)
                sys.exit()
        except IOError: # 读不到uploadIDFile，即没启动过上传任务
            print "First time handle: "+srcfile
            # 启动文件物理分片
            response_indexList = split(srcfile) 
            # 向S3创建Multipart Upload任务，获取UploadID
            reponse_uploadId = createUpload(srcfile) 

        # 获取分片列表
        indexFilename = os.path.join(splitdir, srcfile + '-indexfile.json')  # 1个文件所有分片的索引文件
        indexfile = open(indexFilename, 'r')
        indexList=json.loads(indexfile.read())
        indexfile.close()
        # 执行分片upload
        response_uploadpart = uploadPart(reponse_uploadId, indexList, partnumberList, srcfile)
        print "Last uploaded partnumber: "+response_uploadpart
        print ""

        # 列出S3上全部已完成的Parts
        response_uploadedList = s3client.list_parts(
            Bucket=s3bucket,
            Key=s3key+srcfile,
            UploadId=reponse_uploadId,
        )
        printPartList(response_uploadedList["Parts"]) 
        
        # 等待人工确认后再合并
        if MaunalMerge == 1:
            keyinput = ""
            while keyinput <>"Y":
                keyinput = raw_input("Do you want to process merge? If not, stop and manually merge. (Y/n)")
                if keyinput == "n":
                    sys.exit()
        
        # 合并S3上的文件
        response_complete = completeUpload(reponse_uploadId, response_uploadedList["Parts"], srcfile)
        print ""
        print "Finish: "+json.dumps(response_complete["Location"])

        # 删除本地临时分片文件
        cleanParts(indexList)
        print ""
        print "Clearn local parts complete. "
        print ""
    print "Complete all files in folder: "+srcdir
