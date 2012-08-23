#!/usr/bin/env python

# ===================================
# kafka_system_test_utils.py
# ===================================

import datetime
import inspect
import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback

import system_test_utils

from datetime  import datetime
from time      import mktime

# ====================================================================
# Two logging formats are defined in system_test/system_test_runner.py
# ====================================================================

# 1. "namedLogger" is defined to log message in this format:
#    "%(asctime)s - %(levelname)s - %(message)s %(name_of_class)s"
#    usage: to log message and showing the class name of the message

logger     = logging.getLogger("namedLogger")
thisClassName = '(kafka_system_test_utils)'
d = {'name_of_class': thisClassName}

# 2. "anonymousLogger" is defined to log message in this format:
#    "%(asctime)s - %(levelname)s - %(message)s"
#    usage: to log message without showing class name and it's appropriate
#           for logging generic message such as "sleeping for 5 seconds"

anonLogger = logging.getLogger("anonymousLogger")


# =====================================
# Sample usage of getting testcase env
# =====================================
def get_testcase_env(testcaseEnv):
    anonLogger.info("================================================")
    anonLogger.info("systemTestBaseDir     : " + testcaseEnv.systemTestBaseDir)
    anonLogger.info("testSuiteBaseDir      : " + testcaseEnv.testSuiteBaseDir)
    anonLogger.info("testCaseBaseDir       : " + testcaseEnv.testCaseBaseDir)
    anonLogger.info("testCaseLogsDir       : " + testcaseEnv.testCaseLogsDir)
    anonLogger.info("userDefinedEnvVarDict : (testcaseEnv.userDefinedEnvVarDict)")
    anonLogger.info("================================================")


def get_testcase_config_log_dir_pathname(testcaseEnv, role, entityId, type):

    defaultLogDir = testcaseEnv.testCaseLogsDir + "/" + role + "-" + entityId

    # type is either "metrics" or "dashboards" or "default"
    if type == "metrics":
        return testcaseEnv.testCaseLogsDir + "/" + role + "-" + entityId + "/metrics"
    elif type == "default" :
        return testcaseEnv.testCaseLogsDir + "/" + role + "-" + entityId
    elif type == "dashboards":
        return testcaseEnv.testCaseLogsDir + "/dashboards"
    elif type == "config":
        return testcaseEnv.testCaseBaseDir + "/config"
    else:
        logger.error("unrecognized log directory type : " + type, extra=d)
        logger.error("returning default log dir : " + defaultLogDir, extra=d)
        return defaultLogDir


def generate_testcase_log_dirs(systemTestEnv, testcaseEnv):

    testcasePathName = testcaseEnv.testCaseBaseDir
    logger.debug("testcase pathname: " + testcasePathName, extra=d)

    if not os.path.exists(testcasePathName + "/config") : os.makedirs(testcasePathName + "/config")
    if not os.path.exists(testcasePathName + "/logs")   : os.makedirs(testcasePathName + "/logs")

    dashboardsPathName = testcaseEnv.testCaseLogsDir + "/dashboards"
    if not os.path.exists(dashboardsPathName) : os.makedirs(dashboardsPathName)

    for clusterEntityConfigDict in systemTestEnv.clusterEntityConfigDictList:
        entityId = clusterEntityConfigDict["entity_id"]
        role     = clusterEntityConfigDict["role"]

        logger.debug("entity_id : " + entityId, extra=d)
        logger.debug("role      : " + role,     extra=d)

        metricsPathName = get_testcase_config_log_dir_pathname(testcaseEnv, role, entityId, "metrics")
        if not os.path.exists(metricsPathName) : os.makedirs(metricsPathName)


def collect_logs_from_remote_hosts(systemTestEnv, testcaseEnv):
    anonLogger.info("================================================")
    anonLogger.info("collecting logs from remote machines")
    anonLogger.info("================================================")

    testCaseBaseDir = testcaseEnv.testCaseBaseDir

    for clusterEntityConfigDict in systemTestEnv.clusterEntityConfigDictList:
        hostname   = clusterEntityConfigDict["hostname"]
        entity_id  = clusterEntityConfigDict["entity_id"]
        role       = clusterEntityConfigDict["role"]

        logger.debug("entity_id : " + entity_id, extra=d)
        logger.debug("hostname  : " + hostname,  extra=d)
        logger.debug("role      : " + role,      extra=d)

        configPathName     = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "config")
        metricsPathName    = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "metrics")
        dashboardsPathName = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "dashboards")

        cmdList = ["scp",
                   hostname + ":" + metricsPathName + "/*",
                   metricsPathName]
        cmdStr  = " ".join(cmdList)
        logger.debug("executing command [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr)
 

def generate_testcase_log_dirs_in_remote_hosts(systemTestEnv, testcaseEnv):
    testCaseBaseDir = testcaseEnv.testCaseBaseDir

    for clusterEntityConfigDict in systemTestEnv.clusterEntityConfigDictList:
        hostname   = clusterEntityConfigDict["hostname"]
        entity_id  = clusterEntityConfigDict["entity_id"]
        role       = clusterEntityConfigDict["role"]

        logger.debug("entity_id : " + entity_id, extra=d)
        logger.debug("hostname  : " + hostname, extra=d)
        logger.debug("role      : " + role, extra=d)

        configPathName     = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "config")
        metricsPathName    = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "metrics")
        dashboardsPathName = get_testcase_config_log_dir_pathname(testcaseEnv, role, entity_id, "dashboards")

        cmdList = ["ssh " + hostname,
                   "'mkdir -p",
                   configPathName,
                   metricsPathName,
                   dashboardsPathName + "'"]
        cmdStr  = " ".join(cmdList)
        logger.debug("executing command [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr)


def init_entity_props(systemTestEnv, testcaseEnv):
    clusterConfigsList  = systemTestEnv.clusterEntityConfigDictList
    testcaseConfigsList = testcaseEnv.testcaseConfigsList
    testcasePathName    = testcaseEnv.testCaseBaseDir

    # consumer config / log files location
    consEntityIdList   = system_test_utils.get_data_from_list_of_dicts( \
                             clusterConfigsList, "role", "console_consumer", "entity_id")
    consLogList        = system_test_utils.get_data_from_list_of_dicts( \
                             testcaseConfigsList, "entity_id", consEntityIdList[0], "log_filename")
    consLogPathname    = testcasePathName + "/logs/" + consLogList[0]
    consCfgList        = system_test_utils.get_data_from_list_of_dicts( \
                             testcaseConfigsList, "entity_id", consEntityIdList[0], "config_filename")
    consCfgPathname    = testcasePathName + "/config/" + consCfgList[0]

    # producer config / log files location
    prodEntityIdList   = system_test_utils.get_data_from_list_of_dicts( \
                             clusterConfigsList, "role", "producer_performance", "entity_id")
    prodLogList        = system_test_utils.get_data_from_list_of_dicts( \
                             testcaseConfigsList, "entity_id", prodEntityIdList[0], "log_filename")
    prodLogPathname    = testcasePathName + "/logs/" + prodLogList[0]
    prodCfgList        = system_test_utils.get_data_from_list_of_dicts( \
                             testcaseConfigsList, "entity_id", prodEntityIdList[0], "config_filename")
    prodCfgPathname    = testcasePathName + "/config/" + prodCfgList[0]

    testcaseEnv.userDefinedEnvVarDict["consumerLogPathName"]    = consLogPathname
    testcaseEnv.userDefinedEnvVarDict["consumerConfigPathName"] = consCfgPathname
    testcaseEnv.userDefinedEnvVarDict["producerLogPathName"]    = prodLogPathname
    testcaseEnv.userDefinedEnvVarDict["producerConfigPathName"] = prodCfgPathname


def copy_file_with_dict_values(srcFile, destFile, dictObj):
    infile  = open(srcFile, "r")
    inlines = infile.readlines()
    infile.close()

    outfile = open(destFile, 'w')
    for line in inlines:
        for key in dictObj.keys():
            if (line.startswith(key + "=")):
                line = key + "=" + dictObj[key] + "\n"
        outfile.write(line)
    outfile.close()


def start_metrics_collection(jmxHost, jmxPort, mBeanObjectName, mBeanAttributes, entityId, clusterEntityConfigDictList, testcaseEnv):
    logger.info("starting metrics collection on jmx port: " + jmxPort, extra=d)
    jmxUrl    = "service:jmx:rmi:///jndi/rmi://" + jmxHost + ":" + jmxPort + "/jmxrmi"
    kafkaHome = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "kafka_home")
    javaHome  = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "java_home")
    metricsPathName = get_testcase_config_log_dir_pathname(testcaseEnv, "broker", entityId, "metrics")

    startMetricsCmdList = ["ssh " + jmxHost,
                           "'JAVA_HOME=" + javaHome,
                           "JMX_PORT= " + kafkaHome + "/bin/kafka-run-class.sh kafka.tools.JmxTool",
                           "--jmx-url " + jmxUrl,
                           "--object-name " + mBeanObjectName + " &> ",
                           metricsPathName + "/metrics.csv & echo pid:$! > ",
                           metricsPathName + "/entity_pid'"]
   
    startMetricsCommand = " ".join(startMetricsCmdList) 
    logger.debug("executing command: [" + startMetricsCommand + "]", extra=d)
    system_test_utils.async_sys_call(startMetricsCommand)

    pidCmdStr = "ssh " + jmxHost + " 'cat " + metricsPathName + "/entity_pid'"
    logger.debug("executing command: [" + pidCmdStr + "]", extra=d)
    subproc = system_test_utils.sys_call_return_subproc(pidCmdStr)

    # keep track of the remote entity pid in a dictionary
    for line in subproc.stdout.readlines():
        if line.startswith("pid"):
            line = line.rstrip('\n')
            logger.debug("found pid line: [" + line + "]", extra=d)
            tokens  = line.split(':')
            thisPid = tokens[1]
            testcaseEnv.entityParentPidDict[thisPid] = thisPid


def generate_overriden_props_files(testsuitePathname, testcaseEnv, systemTestEnv):
    logger.info("calling generate_properties_files", extra=d)

    clusterConfigsList = systemTestEnv.clusterEntityConfigDictList
    tcPathname    = testcaseEnv.testCaseBaseDir
    tcConfigsList = testcaseEnv.testcaseConfigsList

    cfgTemplatePathname = os.path.abspath(testsuitePathname + "/config")
    cfgDestPathname     = os.path.abspath(tcPathname + "/config")
    logger.info("config template (source) pathname : " + cfgTemplatePathname, extra=d)
    logger.info("testcase config (dest)   pathname : " + cfgDestPathname, extra=d)

    # loop through all zookeepers (if more than 1) to retrieve host and clientPort
    # to construct a zk.connect str for broker in the form of:
    # zk.connect=<host1>:<port2>,<host2>:<port2>
    zkConnectStr = ""
    zkDictList = system_test_utils.get_dict_from_list_of_dicts(clusterConfigsList, "role", "zookeeper")
    for zkDict in zkDictList:
        entityID       = zkDict["entity_id"]
        hostname       = zkDict["hostname"]
        clientPortList = system_test_utils.get_data_from_list_of_dicts(tcConfigsList, "entity_id", entityID, "clientPort")
        clientPort     = clientPortList[0]

        if ( zkConnectStr.__len__() == 0 ):
            zkConnectStr = hostname + ":" + clientPort
        else:
            zkConnectStr = zkConnectStr + "," + hostname + ":" + clientPort

    # for each entity in the cluster config
    for clusterCfg in clusterConfigsList:
        cl_entity_id = clusterCfg["entity_id"]

        for tcCfg in tcConfigsList:
            if (tcCfg["entity_id"] == cl_entity_id):

                # copy the associated .properties template, update values, write to testcase_<xxx>/config

                if ( clusterCfg["role"] == "broker" ):
                    tcCfg["zk.connect"] = zkConnectStr
                    copy_file_with_dict_values(cfgTemplatePathname + "/server.properties", \
                                               cfgDestPathname + "/" + tcCfg["config_filename"], tcCfg)

                elif ( clusterCfg["role"] == "zookeeper"):
                    copy_file_with_dict_values(cfgTemplatePathname + "/zookeeper.properties", \
                                               cfgDestPathname + "/" + tcCfg["config_filename"], tcCfg)

                elif ( clusterCfg["role"] == "producer_performance"):
                    tcCfg["brokerinfo"] = "zk.connect" + "=" + zkConnectStr
                    copy_file_with_dict_values(cfgTemplatePathname + "/producer_performance.properties", \
                                               cfgDestPathname + "/" + tcCfg["config_filename"], tcCfg)

                elif ( clusterCfg["role"] == "console_consumer"):
                    tcCfg["zookeeper"] = zkConnectStr
                    copy_file_with_dict_values(cfgTemplatePathname + "/console_consumer.properties", \
                                               cfgDestPathname + "/" + tcCfg["config_filename"], tcCfg)
                else:
                    print "    => ", tcCfg
                    print "UNHANDLED key"

    # scp updated config files to remote hosts
    scp_file_to_remote_host(clusterConfigsList, testcaseEnv)


def scp_file_to_remote_host(clusterEntityConfigDictList, testcaseEnv):

    testcaseConfigsList = testcaseEnv.testcaseConfigsList

    for clusterEntityConfigDict in clusterEntityConfigDictList:
        hostname         = clusterEntityConfigDict["hostname"]
        testcasePathName = testcaseEnv.testCaseBaseDir

        cmdStr = "scp " + testcasePathName + "/config/* " + hostname + ":" + testcasePathName + "/config"
        logger.debug("executing command [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr)


def start_zookeepers(systemTestEnv, testcaseEnv):
    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    zkEntityIdList = system_test_utils.get_data_from_list_of_dicts( \
                         clusterEntityConfigDictList, "role", "zookeeper", "entity_id")

    for zkEntityId in zkEntityIdList:
        start_entity_in_background(systemTestEnv, testcaseEnv, zkEntityId)


def start_brokers(systemTestEnv, testcaseEnv):
    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    brokerEntityIdList = system_test_utils.get_data_from_list_of_dicts( \
                             clusterEntityConfigDictList, "role", "broker", "entity_id")

    for brokerEntityId in brokerEntityIdList:
        start_entity_in_background(systemTestEnv, testcaseEnv, brokerEntityId)


def get_leader_elected_log_line(systemTestEnv, testcaseEnv):

    logger.info("looking up leader...", extra=d)

    # keep track of leader related data in this dict such as broker id,
    # entity id and timestamp and return it to the caller function
    leaderDict = {} 

    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList
    brokerEntityIdList = system_test_utils.get_data_from_list_of_dicts( \
                             clusterEntityConfigDictList, "role", "broker", "entity_id")

    for brokerEntityId in brokerEntityIdList:

        hostname   = system_test_utils.get_data_by_lookup_keyval( \
                         clusterEntityConfigDictList, "entity_id", brokerEntityId, "hostname")
        logFile    = system_test_utils.get_data_by_lookup_keyval( \
                         testcaseEnv.testcaseConfigsList, "entity_id", brokerEntityId, "log_filename")

        leaderDict["entity_id"] = brokerEntityId
        leaderDict["hostname"]  = hostname

        logPathName = get_testcase_config_log_dir_pathname(testcaseEnv, "broker", brokerEntityId, "default")
        cmdStrList = ["ssh " + hostname,
                      "\"grep -i -h '" + testcaseEnv.userDefinedEnvVarDict["LEADER_ELECTION_COMPLETED_MSG"] + "' ",
                      logPathName + "/" + logFile + " | ",
                      "sort | tail -1\""]
        cmdStr     = " ".join(cmdStrList)

        logger.debug("executing command [" + cmdStr + "]", extra=d)
        subproc = system_test_utils.sys_call_return_subproc(cmdStr)
        for line in subproc.stdout.readlines():

            line = line.rstrip('\n')

            if testcaseEnv.userDefinedEnvVarDict["LEADER_ELECTION_COMPLETED_MSG"] in line:
                logger.info("found the log line : " + line, extra=d)
                try:
                    matchObj    = re.match(testcaseEnv.userDefinedEnvVarDict["REGX_LEADER_ELECTION_PATTERN"], line)
                    datetimeStr = matchObj.group(1)
                    datetimeObj = datetime.strptime(datetimeStr, "%Y-%m-%d %H:%M:%S,%f")
                    unixTs = time.mktime(datetimeObj.timetuple()) + 1e-6*datetimeObj.microsecond
                    #print "{0:.3f}".format(unixTs)
                    leaderDict["timestamp"] = unixTs
                    leaderDict["brokerid"]  = matchObj.group(2)
                    leaderDict["topic"]     = matchObj.group(3)
                    leaderDict["partition"] = matchObj.group(4)
                except:
                    logger.error("ERROR [unable to find matching leader details: Has the matching pattern changed?]", extra=d)
            #else:
            #    logger.debug("unmatched line found [" + line + "]", extra=d)

    return leaderDict


def start_entity_in_background(systemTestEnv, testcaseEnv, entityId):

    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    # cluster configurations:
    hostname  = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "hostname")
    role      = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "role")
    kafkaHome = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "kafka_home")
    javaHome  = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "java_home")
    jmxPort   = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "jmx_port")

    # testcase configurations:
    testcaseConfigsList = testcaseEnv.testcaseConfigsList
    clientPort = system_test_utils.get_data_by_lookup_keyval(testcaseConfigsList, "entity_id", entityId, "clientPort")
    configFile = system_test_utils.get_data_by_lookup_keyval(testcaseConfigsList, "entity_id", entityId, "config_filename")
    logFile    = system_test_utils.get_data_by_lookup_keyval(testcaseConfigsList, "entity_id", entityId, "log_filename")

    logger.info("starting " + role + " in host [" + hostname + "] on client port [" + clientPort + "]", extra=d)

    configPathName = get_testcase_config_log_dir_pathname(testcaseEnv, role, entityId, "config")
    logPathName    = get_testcase_config_log_dir_pathname(testcaseEnv, role, entityId, "default")

    if role == "zookeeper":
        cmdList = ["ssh " + hostname,
                  "'JAVA_HOME=" + javaHome,
                  kafkaHome + "/bin/zookeeper-server-start.sh ",
                  configPathName + "/" + configFile + " &> ",
                  logPathName + "/" + logFile + " & echo pid:$! > ",
                  logPathName + "/entity_" + entityId + "_pid'"]


        # construct zk.connect str and update it to testcaseEnv.userDefinedEnvVarDict.zkConnectStr
        if ( len(testcaseEnv.userDefinedEnvVarDict["zkConnectStr"]) > 0 ):
            testcaseEnv.userDefinedEnvVarDict["zkConnectStr"] = \
                testcaseEnv.userDefinedEnvVarDict["zkConnectStr"] + "," + hostname + ":" + clientPort
        else:
            testcaseEnv.userDefinedEnvVarDict["zkConnectStr"] = hostname + ":" + clientPort

    elif role == "broker":
        cmdList = ["ssh " + hostname,
                  "'JAVA_HOME=" + javaHome,
                  "JMX_PORT=" + jmxPort,
                  kafkaHome + "/bin/kafka-run-class.sh kafka.Kafka",
                  configPathName + "/" + configFile + " &> ",
                  logPathName + "/" + logFile + " & echo pid:$! > ",
                  logPathName + "/entity_" + entityId + "_pid'"]

    # it seems to be a better idea to launch producer & consumer in separate functions
    # elif role == "producer_performance":
    # elif role == "console_consumer":

    cmdStr = " ".join(cmdList)

    logger.debug("executing command: [" + cmdStr + "]", extra=d)
    system_test_utils.async_sys_call(cmdStr)
    time.sleep(5)

    pidCmdStr = "ssh " + hostname + " 'cat " + logPathName + "/entity_" + entityId + "_pid'"
    logger.debug("executing command: [" + pidCmdStr + "]", extra=d)
    subproc = system_test_utils.sys_call_return_subproc(pidCmdStr)

    # keep track of the remote entity pid in a dictionary
    for line in subproc.stdout.readlines():
        if line.startswith("pid"):
            line = line.rstrip('\n')
            logger.debug("found pid line: [" + line + "]", extra=d)
            tokens = line.split(':')
            testcaseEnv.entityParentPidDict[entityId] = tokens[1]

    # if it is a broker, start metric collection
    if role == "broker":
        start_metrics_collection(hostname, jmxPort, "kafka:type=kafka.SocketServerStats", \
            "AvgFetchRequestMs, AvgProduceRequestMs", entityId, clusterEntityConfigDictList, testcaseEnv)


def start_console_consumer(systemTestEnv, testcaseEnv):

    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    consumerConfigList = system_test_utils.get_dict_from_list_of_dicts(clusterEntityConfigDictList, "role", "console_consumer")
    for consumerConfig in consumerConfigList:
        host              = consumerConfig["hostname"]
        entityId          = consumerConfig["entity_id"]
        kafkaHome         = system_test_utils.get_data_by_lookup_keyval( \
                                clusterEntityConfigDictList, "entity_id", entityId, "kafka_home")
        javaHome          = system_test_utils.get_data_by_lookup_keyval( \
                                clusterEntityConfigDictList, "entity_id", entityId, "java_home")
        kafkaRunClassBin  = kafkaHome + "/bin/kafka-run-class.sh"

        logger.info("starting console consumer", extra=d)

        consumerLogPathName = get_testcase_config_log_dir_pathname(testcaseEnv, "console_consumer", entityId, "default") + \
                                  "/console_consumer.log"

        testcaseEnv.userDefinedEnvVarDict["consumerLogPathName"] = consumerLogPathName

        commandArgs = system_test_utils.convert_keyval_to_cmd_args(testcaseEnv.userDefinedEnvVarDict["consumerConfigPathName"])
        cmdList = ["ssh " + host,
                   "'JAVA_HOME=" + javaHome,
                   kafkaRunClassBin + " kafka.consumer.ConsoleConsumer",
                   commandArgs + " &> " + consumerLogPathName + "'"]

        cmdStr = " ".join(cmdList)
        logger.debug("executing command: [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr)



def start_producer_performance(systemTestEnv, testcaseEnv):

    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    producerConfigList = system_test_utils.get_dict_from_list_of_dicts( \
                             clusterEntityConfigDictList, "role", "producer_performance")
    for producerConfig in producerConfigList:
        host              = producerConfig["hostname"]
        entityId          = producerConfig["entity_id"]
        kafkaHome         = system_test_utils.get_data_by_lookup_keyval( \
                                clusterEntityConfigDictList, "entity_id", entityId, "kafka_home")
        javaHome          = system_test_utils.get_data_by_lookup_keyval( \
                                clusterEntityConfigDictList, "entity_id", entityId, "java_home")
        kafkaRunClassBin  = kafkaHome + "/bin/kafka-run-class.sh"

        logger.info("starting producer preformance", extra=d)

        producerLogPathName = get_testcase_config_log_dir_pathname(testcaseEnv, "producer_performance", entityId, "default") + \
                                  "/producer_performance.log"

        testcaseEnv.userDefinedEnvVarDict["producerLogPathName"] = producerLogPathName

        commandArgs = system_test_utils.convert_keyval_to_cmd_args(testcaseEnv.userDefinedEnvVarDict["producerConfigPathName"])
        cmdList = ["ssh " + host,
                   "'JAVA_HOME=" + javaHome,
                   kafkaRunClassBin + " kafka.perf.ProducerPerformance",
                   commandArgs + " &> " + producerLogPathName + "'"]

        cmdStr = " ".join(cmdList)
        logger.debug("executing command: [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr) 


def stop_remote_entity(systemTestEnv, entityId, parentPid):
    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    hostname  = system_test_utils.get_data_by_lookup_keyval(clusterEntityConfigDictList, "entity_id", entityId, "hostname")
    pidStack  = system_test_utils.get_remote_child_processes(hostname, parentPid)

    logger.info("terminating process id: " + parentPid + " in host: " + hostname, extra=d)
    system_test_utils.sigterm_remote_process(hostname, pidStack)
    time.sleep(1)
    system_test_utils.sigkill_remote_process(hostname, pidStack)


def create_topic(systemTestEnv, testcaseEnv):
    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    prodPerfCfgList = system_test_utils.get_dict_from_list_of_dicts( \
                          clusterEntityConfigDictList, "role", "producer_performance")
    prodPerfCfgDict = system_test_utils.get_dict_from_list_of_dicts( \
                          testcaseEnv.testcaseConfigsList, "entity_id", prodPerfCfgList[0]["entity_id"])
    prodTopicList   = prodPerfCfgDict[0]["topic"].split(',')

    zkEntityId      = system_test_utils.get_data_by_lookup_keyval( \
                          clusterEntityConfigDictList, "role", "zookeeper", "entity_id")
    zkHost          = system_test_utils.get_data_by_lookup_keyval( \
                          clusterEntityConfigDictList, "role", "zookeeper", "hostname")
    kafkaHome       = system_test_utils.get_data_by_lookup_keyval( \
                          clusterEntityConfigDictList, "entity_id", zkEntityId, "kafka_home")
    javaHome        = system_test_utils.get_data_by_lookup_keyval( \
                          clusterEntityConfigDictList, "entity_id", zkEntityId, "java_home")
    createTopicBin  = kafkaHome + "/bin/kafka-create-topic.sh"

    logger.info("zkEntityId : " + zkEntityId, extra=d)
    logger.info("createTopicBin : " + createTopicBin, extra=d)

    for topic in prodTopicList:
        logger.info("creating topic: [" + topic + "] at: [" + testcaseEnv.userDefinedEnvVarDict["zkConnectStr"] + "]", extra=d) 
        cmdList = ["ssh " + zkHost,
                   "'JAVA_HOME=" + javaHome,
                   createTopicBin,
                   " --topic "     + topic,
                   " --zookeeper " + testcaseEnv.userDefinedEnvVarDict["zkConnectStr"],
                   " --replica "   + testcaseEnv.testcaseArgumentsDict["replica_factor"],
                   " --partition " + testcaseEnv.testcaseArgumentsDict["num_partition"] + " &> ",
                   testcaseEnv.testCaseBaseDir + "/logs/create_topic.log'"]

        cmdStr = " ".join(cmdList)
        logger.debug("executing command: [" + cmdStr + "]", extra=d)
        subproc = system_test_utils.sys_call_return_subproc(cmdStr)


def get_message_id(logPathName):
    logLines      = open(logPathName, "r").readlines()
    messageIdList = []

    for line in logLines:
        if not "MessageID" in line:
            continue
        else:
            matchObj = re.match('.*MessageID:(.*?):', line)
            messageIdList.append( matchObj.group(1) )

    return messageIdList


def validate_data_matched(systemTestEnv, testcaseEnv):
    validationStatusDict        = testcaseEnv.validationStatusDict
    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList

    producerEntityId = system_test_utils.get_data_by_lookup_keyval( \
                           clusterEntityConfigDictList, "role", "producer_performance", "entity_id")
    consumerEntityId = system_test_utils.get_data_by_lookup_keyval( \
                           clusterEntityConfigDictList, "role", "console_consumer", "entity_id")
    msgIdMissingInConsumerLogPathName = get_testcase_config_log_dir_pathname( \
                           testcaseEnv, "console_consumer", consumerEntityId, "default") + \
                           "/msg_id_missing_in_consumer.log"

    producerMsgIdList  = get_message_id(testcaseEnv.userDefinedEnvVarDict["producerLogPathName"])
    consumerMsgIdList  = get_message_id(testcaseEnv.userDefinedEnvVarDict["consumerLogPathName"])
    producerMsgIdSet   = set(producerMsgIdList)
    consumerMsgIdSet   = set(consumerMsgIdList)

    missingMsgIdInConsumer = producerMsgIdSet - consumerMsgIdSet

    outfile = open(msgIdMissingInConsumerLogPathName, "w")
    for id in missingMsgIdInConsumer:
        outfile.write(id + "\n")
    outfile.close()

    logger.info("no. of unique messages sent from publisher  : " + str(len(producerMsgIdSet)), extra=d)
    logger.info("no. of unique messages received by consumer : " + str(len(producerMsgIdSet)), extra=d)

    if ( len(missingMsgIdInConsumer) == 0 and len(producerMsgIdSet) > 0 ):
        validationStatusDict["Validate for data matched"] = "PASSED"
        return True
    else:
        validationStatusDict["Validate for data matched"] = "FAILED"
        logger.info("See " + msgIdMissingInConsumerLogPathName + " for missing MessageID", extra=d)
        return False
     

def validate_leader_election_successful(testcaseEnv, leaderDict, validationStatusDict):

    if ( len(leaderDict) > 0 ):
        try:
            leaderBrokerId = leaderDict["brokerid"]
            leaderEntityId = leaderDict["entity_id"]
            leaderPid      = testcaseEnv.entityParentPidDict[leaderEntityId]
            hostname       = leaderDict["hostname"]

            logger.info("found leader in entity [" + leaderEntityId + "] with brokerid [" + \
                leaderBrokerId + "] for partition [" + leaderDict["partition"] + "]", extra=d)
            validationStatusDict["Validate leader election successful"] = "PASSED"
            return True
        except Exception, e:
            logger.error("leader info not completed:", extra=d)
            validationStatusDict["Validate leader election successful"] = "FAILED"
            print leaderDict
            print e
            return False
    else:
        validationStatusDict["Validate leader election successful"] = "FAILED"
        return False


def cleanup_data_at_remote_hosts(systemTestEnv, testcaseEnv):

    clusterEntityConfigDictList = systemTestEnv.clusterEntityConfigDictList
    testcaseConfigsList         = testcaseEnv.testcaseConfigsList

    for clusterEntityConfigDict in systemTestEnv.clusterEntityConfigDictList:

        hostname         = clusterEntityConfigDict["hostname"]
        entityId         = clusterEntityConfigDict["entity_id"]
        role             = clusterEntityConfigDict["role"]
        #testcasePathName = testcaseEnv.testcaseBaseDir
        cmdStr           = ""
        dataDir          = ""

        logger.info("cleaning up data dir on host: [" + hostname + "]", extra=d)

        if role == 'zookeeper':
            dataDir = system_test_utils.get_data_by_lookup_keyval(testcaseConfigsList, "entity_id", entityId, "dataDir")
        elif role == 'broker':
            dataDir = system_test_utils.get_data_by_lookup_keyval(testcaseConfigsList, "entity_id", entityId, "log.dir")
        else:
            logger.info("skipping role [" + role + "] on host : [" + hostname + "]", extra=d)
            continue

        cmdStr  = "ssh " + hostname + " 'rm -r " + dataDir + "/*'"

        if not dataDir.startswith("/tmp"):
            logger.warn("possible destructive command [" + cmdStr + "]", extra=d)
            logger.warn("check config file: system_test/cluster_config.properties", extra=d)
            logger.warn("aborting test...", extra=d)
            sys.exit(1)

        logger.debug("executing command [" + cmdStr + "]", extra=d)
        system_test_utils.sys_call(cmdStr)

    
