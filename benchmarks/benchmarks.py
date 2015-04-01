# -*- coding: utf-8 -*-
"""
Fonctions testant le temps d'execution de chacune des taches du core
"""

import timeit
from datetime import datetime, timedelta
import random
from cide.app.python.core import Core
import logging
import gc
from Queue import Queue
from pdb import set_trace as debug
from libZoneTransit import Addition

class Benchmarks(object):
  def __init__(self):
      
    self.project_conf = dict(name = 'Benchmarks',
                base_dir = './temp',
                code_dir = './temp',
                exec_dir = './temp',
                backup_dir = './temp',
                tmp_dir = './temp')
    
    #Not used since tasks are called directly              
    self.core_conf = dict(cycle_time = 0.0, 
                 buffer_critical = 0.0,
                 buffer_secondary = 0.0,
                 buffer_auxiliary = 0.0)
                 
    # Setup Log
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    handler = logging.FileHandler("log_benchmarks")
    handler.setFormatter(formatter)
    self.logger = logging.getLogger('cide.py')
    self.logger.setLevel(logging.DEBUG)
    self.logger.addHandler(handler)
    
    self.core = None
    self.callers = []
    self.files = []
    self.changes = []
    
    for i in range(50):
        self.callers.append(chr(ord('a')+i / 26) + chr(ord('a')+i % 26))
        filename = ""
        for j in range(random.randint(1,100)):
            filename += '/' + chr(ord('a')+i / 26) + chr(ord('a')+i % 26)
        self.files.append(filename)     
            
  def setUp(self):
    self.core = Core(self.project_conf, self.core_conf, self.logger)
      
    for file in self.files:
      self.core.add_file(file)
 
    #Register all users to all files
    for file in self.files:
        for user in self.callers:
            self.core._task_open_file(user, file)
 
    #One change per user per file 
    for file in self.files:
        for user in self.callers:
            self.core._task_file_edit(file, [Core.Change(0,"Hello",True)],user)
            
  def tearDown(self):
    self.core = None

  def benchmarks_task_get_project_nodes(self):
    print 'Test de _task_get_project_nodes'
    caller = random.choice(self.callers)
    self.myTimeIt(lambda: self.core._task_get_project_nodes(caller))
    print ' '

  def benchmarks_task_get_file_content(self):
    print 'Test de _task_get_file_content'
    caller = random.choice(self.callers)
    file = random.choice(self.files)
    self.myTimeIt(lambda: self.core._task_get_file_content(file,caller))
    print ' '

  def benchmarks_task_open_file(self):
    print 'Test de _task_open_file'
    user = random.choice(self.callers)
    file = random.choice(self.files)
    self.myTimeIt(lambda: self.core._task_open_file(user,file))
    print ' '
      
  def benchmarks_task_unregister_user_to_file(self):
    print 'Test de _task_unregister_user_to_file'
    user = random.choice(self.callers)
    file = random.choice(self.files)
    self.myTimeIt(lambda: self.core._task_unregister_user_to_file(user,file))
    print ' '
    
  def benchmarks_task_unregister_user_to_all_files(self):
    print 'Test de _task_unregister_user_to_all_files'
    user = random.choice(self.callers)
    self.myTimeIt(lambda: self.core._task_unregister_user_to_all_files(user))
    print ' '
      
  def benchmarks_task_file_edit(self):
    print 'Test de _task_file_edit'
    file = random.choice(self.files)
    user = random.choice(self.callers)
    self.myTimeIt(lambda: self.core._task_file_edit(file, [Core.Change(0,"Hello",True)],user))
    print ' '
    
  def benchmarks_task_check_apply_notify(self):
    print 'Test de task_check_apply_notify'
    self.myTimeIt(lambda: self.core.task_check_apply_notify())
    print ' '
    
  def benchmarks_task_create_archive(self):
    print 'Test de _task_create_archive'
    caller = random.choice(self.callers)
    self.myTimeIt(lambda: self.core._task_create_archive('.', caller, Queue()))
    print ' '
    
  def myTimeIt(self, function, n=1000):
    times = []
    for i in range(n):
      self.setUp()
      startTime = datetime.now()
      function()
      endTime = datetime.now()
      self.tearDown()
      times.append(endTime - startTime)
    
    print '3 first are : {0} {1} {2}'.format(times[0],times[1],times[2])
    print '3 last are : {0} {1} {2}'.format(times[len(times)-1], times[len(times)-2], times[len(times)-3])    
    
    times.sort()
    print '10 best are : {0} {1} {2} {3} {4} {5} {6} {7} {8} {9}'.format(times[0],times[1],times[2],times[3],times[4],times[5],times[6],times[7],times[8],times[9])
    print '10 worst are : {0} {1} {2} {3} {4} {5} {6} {7} {8} {9}'.format(times[len(times)-1], times[len(times)-2], times[len(times)-3],times[len(times)-4],times[len(times)-5],times[len(times)-6],times[len(times)-7],times[len(times)-8],times[len(times)-9],times[len(times)-10])
    
    print 'best case is : {0}'.format(min(times))     
    print 'worst case is : {0}'.format(max(times))
    print 'average is: {0}'.format((reduce(lambda x, y: x + y, times)/len(times)))
    
benchmarks = Benchmarks()
benchmarks.benchmarks_task_get_project_nodes()
benchmarks.benchmarks_task_get_file_content()
benchmarks.benchmarks_task_open_file()
benchmarks.benchmarks_task_unregister_user_to_file()
benchmarks.benchmarks_task_unregister_user_to_all_files()
benchmarks.benchmarks_task_file_edit()
benchmarks.benchmarks_task_check_apply_notify()
benchmarks.benchmarks_task_create_archive()
