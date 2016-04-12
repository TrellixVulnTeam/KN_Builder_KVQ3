"""

Class Description:

Used to benchmark database functionalities

Utilizes performane queries described in https://fromdual.com/mysql-performance-schema-hints

"""

from datetime import datetime
import config_utilities as cf
import mysql.connector as sql
import os
import json
import subprocess
import elasticsearch
from time import time
import threading
import logging
from time import time, sleep
from random import randrange, sample
import math
import sys

class MySQLBenchmark:
    """
    Attributes:
        host (str): the MySQL db hostname
        user (str): the MySQL db username
        port (str): the MySQL db port
        passw (str): the MySQL db password
        database (str): the MySQL database to connect to
        conn (object): connection object for the database
        cursor (object): cursor object for the database
    
    """

    def __init__(self, database=None, args=cf.config_args()):
        """Init a MySQLBenchmark Object
        
        Args:
        database (str): the MySQL database to connect to (optional)
        """
        self.user = cf.DEFAULT_MYSQL_USER
        self.host = cf.DEFAULT_MYSQL_URL
        #print(self.host)
        self.port = cf.DEFAULT_MYSQL_PORT
        self.passw = cf.DEFAULT_MYSQL_PASS
        #print(self.passw)
        self.database = "KnowNet"
        self.args = args
        if self.database is None:
            self.conn = sql.connect(host=self.host, port=self.port,
                                    user=self.user, password=self.passw,
                                    client_flags=[sql.ClientFlag.LOCAL_FILES])
        else:
            self.conn = sql.connect(host=self.host, port=self.port,
                                    user=self.user, password=self.passw,
                                    db=self.database,
                                    client_flags=[sql.ClientFlag.LOCAL_FILES])
        self.cursor = self.conn.cursor(buffered=True)
    
    def set_buffered_cursor(self):
        """
        Description: 
        Sets the cursor to be a dictionary Cursor
        """
        self.cursor = self.conn.cursor(dictionary=True)
        

    def set_dictionary_cursor(self):
        """
        Description: 
        Sets the cursor to be a dictionary Cursor
        """
        self.cursor = self.conn.cursor(buffered=True)

    """
    Description: The database has to be configured to be able to generate the
    statistics for queries that we use. This is as per the following document: 
    http://www.pythian.com/blog/mysql-query-profiling-with-performance-schema/
    
    ** This is a one-time setup of the database so we must first verify that this 
    step has not already been configured. **
    """
    def check_db_set_for_profiling(self):
        
        check_query = "SELECT * FROM performance_schema.setup_consumers where name = 'events_statements_history_long' OR name = 'events_stages_history_long';"
        self.cursor.execute(check_query)
        result = self.cursor.fetchall()
        if(len(result) != 2):
            print("Error executing check query or unexpected output.")
            return False
        else:
            if(result[0][1] != 'YES' or result[1][1] != 'YES'):
                return False
            else:
                return True
            
        
    def config_db_for_profiling(self):
        '''
        Description:
        
        Function that is used to activate the MySQL performance monitoring components and performance schemas
        
        '''
        #This enables the stage* performance tables"
        config_query1 = "update performance_schema.setup_instruments set enabled='YES', timed='YES';"    
        #This enables the events_statements_history* and events_stages_history* performance  tables
        config_query2 = "update performance_schema.setup_consumers set enabled='YES';"


        #Need to check if permissions are allowed for the user to make this adjustment
        self.cursor.execute(config_query1)
        self.cursor.execute(config_query2)
        print("The database has been configured for performance statisics and analysis.")

            
    def __checkequalbins(self, bin_list, total, percentallowance):
        '''
        Description:
        
        Private method used to determine if the bins are at least percentallowance * total
        This is a test to see if the bins are mostly reasonably sized bins
        '''
        allowance = int(percentallowance*total)
        print("The allowance is "+str(allowance))
        
        for bin_size in bin_list:
            if(bin_size < allowance):
                return False
   
        return True
    
    def gettabledetails(self, tablename):
        '''
        Description:
        
        Uses the MySQL 'DESCRIBE' keyword to extract the Table metadata

        '''
        desc_query = "DESCRIBE "+str(tablename)
        table_desc = []
        for result in self.cursor.execute(desc_query,multi=True):
            res = result.fetchall()
            for field in res:
                data = {}
                data['Field'] = field[0]
                data['Type'] = field[1]
                data['Null'] = field[2]
                data['Key'] = field[3]
                data['Default'] = field[4]
                data['Extra'] = field[5]
                table_desc.append(data)

        return table_desc
        
    def query_execution_time(self, query, query_type):
        '''
        Description: Obtains the total query execution time ("time taken for connection to server and exporting resultset from database) for the given query string and the dabtabase time (amount of time spent generating the query at the database level)
        '''
        db_execution_time = -1
        db_execution_query = "SELECT TRUNCATE(TIMER_WAIT/1000000000000,6) as Duration FROM performance_schema.events_statements_history_long WHERE SQL_TEXT = '"+str(query)+"' order by END_EVENT_ID desc limit 1"
        
        result = None
        
        print(query)
        start = time()
        self.cursor.execute(query)
        if(query_type == 1):
            result = self.cursor.fetchall()
            self.conn.commit()
        elif(query_type == 2):
            self.conn.commit()
        end = time()
        
        self.cursor.execute(db_execution_query)
        timing_data = self.cursor.fetchall()
        self.conn.commit()
        print(timing_data)
        total_time = end-start;

        if(len(timing_data) == 0):
            print("Database not configured for query statistics so we will not generate database time for query execution.")
            print("The total time taken to execute QUERY: "+query+ " is "+str(total_time))

            return result, total_time, None

        else:
            print("Absolute Time taken to execute QUERY: "+query+", is "+str(total_time)+" and real time is "+str(timing_data[0][0]))
        
            return result, total_time, float(timing_data[0][0])
        
    def get_query_id(self, query):
        '''
        Description:
        
        Gets the unique query ID for the latest query that is of the query string provided.
        Obtains the latest query ID by ordering the data by END_EVENT_ID and limiting the resultset to 1
        '''
        get_id_query = "SELECT END_EVENT_ID, TRUNCATE(TIMER_WAIT/1000000000000,6) as Duration, SQL_TEXT FROM performance_schema.events_statements_history_long WHERE SQL_TEXT = '"+str(query)+"' order by END_EVENT_ID desc limit 1;"
        #print(get_id_query)
        
        #Extracting query_id for the provided query string
        self.cursor.execute(get_id_query)
        qids = self.cursor.fetchall()
        if(qids == None or len(qids) == 0):
            print("Query does not exist in history or performance schema not enabled.")
        else:
            return qids[0][0]
    
    def get_query_type(self, query):
        '''
        Description:
        
        Used to determine the query type for a past query (E.g. statement/sql/select)
        '''
        get_type_query = "SELECT EVENT_NAME FROM performance_schema.events_statements_history_long WHERE SQL_TEXT = '"+str(query)+"' order by END_EVENT_ID desc limit 1;"
        #print(get_id_query)
        
        #Extracting query_id for the provided query string
        self.cursor.execute(get_type_query)
        type_data = self.cursor.fetchall()
        if(type_data == None or len(type_data) == 0):
            print("Query does not exist in history or performance schema not enabled.")
        else:
            return type_data[0][0]
    
    def schema_storage_info(self, database):
        """
        Description:
        
        Produces storage capacity information for database schema specified.
        If 'ALL' is the specified database, it will return database information of all
        database except those that are in a MySQL server by default
        
        """
        
        if(database == "ALL"):
            storage_info_query = "SELECT table_schema AS `schema`, engine, COUNT(*) AS `tables`, ROUND(SUM(data_length)/1024/1024, 0) AS data_mb, ROUND(SUM(index_length)/1024/1024, 0) index_mb FROM information_schema.tables WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema') AND engine IS NOT NULL GROUP BY table_schema, engine;"
        else:
            storage_info_query = "SELECT table_schema AS `schema`, engine, COUNT(*) AS `tables`, ROUND(SUM(data_length)/1024/1024, 0) AS data_mb, ROUND(SUM(index_length)/1024/1024, 0) index_mb FROM information_schema.tables WHERE table_schema ='"+str(database)+"' AND engine IS NOT NULL GROUP BY table_schema, engine;"
        #print(get_id_query)
        #Extracting query_id for the provided query string
        storage_desc = []
        for result in self.cursor.execute(storage_info_query,multi=True):
            res = result.fetchall()
            for field in res:
                data = {}
                data['schema'] = field[0]
                data['engine'] = field[1]
                data['tables'] = field[2]
                data['data_mb'] = float(field[3])
                data['index_mb'] = float(field[4])
                storage_desc.append(data)

        return storage_desc
        
        
    def query_time_breakdown(self,query):
        """
        Description: 
        
        Obtains the breakdown of generating the MySQL query in terms of seconds
        """
        #self.cursor.execute(query)
        #self.cursor.fetchall()
        id = self.get_query_id(query)
        print(id)
        query_breakdown_query ="SELECT event_name AS Stage, TRUNCATE(TIMER_WAIT/1000000000000,6) AS Duration FROM performance_schema.events_stages_history_long WHERE END_EVENT_ID="+str(id)+";"
        self.cursor.execute(query_breakdown_query)
        print(self.cursor.fetchall())
    
    def query_execution_plan(self, query):
        explain_query = "EXPLAIN EXTENDED  "+str(query)+""
        execution_plan = []
        for result in self.cursor.execute(explain_query,multi=True):
            res = result.fetchall()
            for step in res:
                data = {}
                data['id'] = step[0]
                data['select_type'] = step[1]
                data['table'] = step[2]
                data['type'] = step[3]
                data['possible_keys'] = step[4]
                data['key'] = step[5]
                data['key_len'] = step[6]
                data['ref'] = step[7]
                data['rows'] = step[8]
                data['filtered'] = step[9]
                data['Extra'] = step[10]
                execution_plan.insert(0,data)
        print(execution_plan)
        return execution_plan

    def get_table_wait_summary(self, table):
        '''
        Description:

        Extracting table wait summaries for READ, WRITE, UPDATE and DELETE operations
        '''
        if(table == "ALL"):
            table_wait_query = "select * from performance_schema.table_io_waits_summary_by_table where count_star > 0;";
        else:
            table_wait_query = "select * from performance_schema.table_io_waits_summary_by_table where OBJECT_NAME='"+table+"' and count_star > 0;"
            
        table_wait_desc = []
        
        #Use the dictionary cursor to generate the wait data as the data is large.
        self.set_dictionary_cursor()
        
        for result in self.cursor.execute(table_wait_query,multi=True):
            columns = [column[0] for column in self.cursor.description]
            res = result.fetchall()
            for row in res:
                table_wait_desc.append(dict(zip(columns, row)))
        
        #print(table_wait_desc)

        #setting back to buffered cursor
        self.set_buffered_cursor()

        return table_wait_desc
    

    def send_data_to_ES(self, ES_host, port, data):
        '''
        Description:
        
        Sends data to a specified elasticsearch instance
        
        Needs work to parametrize the ES host, port and index of access.
        '''
        es = elasticsearch.Elasticsearch([{'host': ES_host, 'port': port}])  # use default of localhost, port 9200
        data[0]['timestamp'] = datetime.now() 
        try:
            res = es.index(index='database_perf', doc_type='benchmark_data', id=1, body=data[0])
        except Exception:
            print("Error connecting to server instance...")
            
        #print(res['created'])

    def connection_stress_test(self, stress_level):
        '''
        Description: 

        Stress Test to test for average connection time to database over a given stress level
        '''
        start = time()
        for i in range(stress_level):
            conn = sql.connect(host=self.host, port=self.port, user=self.user, password=self.passw, client_flags=[sql.ClientFlag.LOCAL_FILES])
            conn.close();

        end = time()
        print("Time taken to execute connections: %d is %f", stress_level, (end-start))
                
    
    def multithreaded_stress_test(self, table, key, set_serialized):
        """
        Description:
        
        Benchmarks lock performance a series of multithreaded inserts into database
        Implements a huerisitic to generate equal partition bins of size 10 of the data.
        """

        heuristic_indexes = [0,1,2,3,4,5,6,7,8,9]
        selected_heuristic = -1
        minbinproportion = 0.05
        
        for heuristic in heuristic_indexes:
            heuristic_query = "select CAST(substring(tmp."+key+",char_length(tmp."+key+")-"+str(heuristic)+",1) AS UNSIGNED) as bin, count(*) from (select * from "+table+") as tmp group by bin;"
            
            total = 0
            tmp_list = []
            
            for result in self.cursor.execute(heuristic_query,multi=True):
                res = result.fetchall()
                
                for step in res:
                    total = total + int(step[1])
                    tmp_list.append(int(step[1]))
                    
            if(self.__checkequalbins(tmp_list, total, 0.05)):
                selected_heuristic = heuristic
                print("The huerisitic value is "+str(selected_heuristic))
                break
        
        #Check to determine if there is a selected heuristic value that meets the checkequalbins requirement
        if(selected_heuristic == -1):
            print("The heuristics provided are unable to select a proportionately-sized bin samples where each bin contains at least "+str(minbinproportion*100.0)+"% of the dataset.")
            sys.exit(0)
    
        threads = []
        thread_data = {'num_threads':len(heuristic_indexes),'total_time':0.0,'thread_timings':[]}
        for i in heuristic_indexes:
            multithreaded_query = "select * from (select CAST(substring(tmp."+key+",char_length(tmp."+key+")-"+str(selected_heuristic)+",1) AS UNSIGNED) as bin, tmp.* from (select * from "+table+") as tmp) as data where data.bin="+str(i)+"";
            threads.append(BenchmarkWorker(self.host,self.port,self.user,self.passw,self.database, multithreaded_query))

        startt = time()
        if(not set_serialized):
            for th in threads:
                # This causes the thread to run()
                th.start() 
                
            for th in threads:
                # This waits until the thread has completed
                th.join() 
                #thread_data['total_time'] += th.execution_time
                thread_data['thread_timings'].append(th.execution_time)
            thread_data['total_time'] =  time() - startt 
            print(thread_data)
        else:
            for th in threads:
                # This causes the thread to run()
                th.start()
                th.join()
                #thread_data['total_time'] += th.execution_time
                thread_data['thread_timings'].append(th.execution_time)
            thread_data['total_time'] =  time() - startt
            print(thread_data)
            

        
    def overlapping_multithreaded_select_test(self, table, key, percentoverlap):
        """
        Description:
        
        Used to benchmark database functions when there are overlapping selects being
        done by multiple connections. Identifies lock bottlenecks.
        """
        heuristic_indexes = [0,1,2,3,4,5,6,7,8,9]
        selected_heuristic = -1
        minbinproportion = 0.05
        
        for heuristic in heuristic_indexes:
            heuristic_query = "select CAST(substring(tmp."+key+",char_length(tmp."+key+")-"+str(heuristic)+",1) AS UNSIGNED) as bin, count(*) from (select * from "+table+") as tmp group by bin;"
            
            total = 0
            tmp_list = []
            
            for result in self.cursor.execute(heuristic_query,multi=True):
                res = result.fetchall()
                
                for step in res:
                    total = total + int(step[1])
                    tmp_list.append(int(step[1]))
                    
            if(self.__checkequalbins(tmp_list, total, minbinproportion)):
                selected_heuristic = heuristic
                print("The huerisitic value is "+str(selected_heuristic))
                break
        
        #Check to determine if there is a selected heuristic value that meets the checkequalbins requirement
        if(selected_heuristic == -1):
            print("The heuristics provided are unable to select a proportionately-sized bin samples where each bin contains at least "+str(minbinproportion*100.0)+"% of the dataset.")
            sys.exit(0)
                    
    
        threads = []
        thread_data = {'num_threads':len(heuristic_indexes),'total_time':0.0,'thread_timings':[]}
        for i in heuristic_indexes:
            new_list = [x for x in heuristic_indexes if x!=i]
            bins = sample(set(heuristic_indexes),int(percentoverlap*10))
            multithreaded_query = "select * from (select CAST(substring(tmp."+key+",char_length(tmp."+key+")-"+str(selected_heuristic)+",1) AS UNSIGNED) as bin, tmp.* from (select * from "+table+") as tmp) as data where data.bin="+str(i)+""
            for bin in bins:
                multithreaded_query += " OR data.bin="+str(bin)+""
            
            threads.append(BenchmarkWorker(self.host,self.port,self.user,self.passw,self.database, multithreaded_query))

        for th in threads:
            # This causes the thread to run()
            th.start() 
            
        for th in threads:
            # This waits until the thread has completed
            th.join() 
            thread_data['total_time'] += th.execution_time
            thread_data['thread_timings'].append(th.execution_time)
        print(thread_data)
        

class BenchmarkWorker(threading.Thread):
    def __init__(self, host, port, user, password, database, query):
        #super(BenchmarkWorker, self).__init__()
        #self._stop = threading.Event()
        threading.Thread.__init__(self)
        self.threadLock = threading.Lock()
        self.query = query
        self.database = database
        self.conn = sql.connect(host=host, port=port,
                                user=user, password=password,
                                db=database,
                                client_flags=[sql.ClientFlag.LOCAL_FILES])
        self.execution_time = None
        
    #def stopit(self):
    #    print("Stoppping...")
    #    self._stop.set()
        
    #def stopped(self):
    #    return self._stop.is_set()
            
    def run(self):
        print("Starting with query: "+self.query)
        #while not self.stopped():                
        cur = self.conn.cursor()
        start = time()
        try:
            cur.execute(self.query)
            res = cur.fetchall()
            #self.conn.commit()
        except Exception as e:
            print("Thread terminating with "+str(e))
            sys.exit(0)
        end = time()
        cur.close()
        self.conn.close()
        self.threadLock.acquire()
        print("The total time taken to run query: "+self.query+" is "+str(end-start))
        self.execution_time = end-start
        #logging.info('Selecting %s rows from indexes between [%s, %s] took %.2f seconds...' % (settings.SELECT_ROW_COUNT, self.id_min, self.id_max, (end - start),))
        self.threadLock.release()
