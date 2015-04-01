import sys
import os
import shutil
from Queue import Queue, Empty as EmptyQueue
from copy import deepcopy
from threading import Thread
from collections import namedtuple
from datetime import datetime, timedelta
from zipfile import ZipFile
from tempfile import NamedTemporaryFile

from cide.app.python.utils.nodes import (get_existing_files,
                                         get_existing_dirs)

# Other stategies will be used but are not required
from cide.app.python.utils.strategies import (StrategyCallEmpty)

from libZoneTransit import (TransitZone as EditBuffer,
                            Addition as EditAdd,
                            Removal as EditRemove,
                            Modifications)


def task_time(microseconds):
  """
  Function decorator to specify the worse execution time metadata
  to a task under the 'time' attribute as a timedelta object

  @type microseconds: float

  @param microseconds: The execution time found by worse case scenarios benchmarks
  """
  def wrapper(func):
    func.time = timedelta(microseconds=microseconds)
    func.debugname = func.func_name
    return func
  return wrapper


class Core(object):
  """
  Cide.py core app module
  """

  # Class to hold every change element using a name
  # Data field would be the content if is_add is True and the count when False
  Change = namedtuple('Change', ['pos', 'data', 'is_add'])

  # Not global as it only refers to the application only
  # Tuple to hold const pair (transitZone, user registered to changes)
  FileUserPair = namedtuple('FileUserPair', ['file', 'users'])

  # Task wrapper to hold the arguments to be applied on a delayed
  # executing function
  Task = namedtuple('Task', ['f', 'args'])

  def __init__(self, project_conf, core_conf, logger):
    """
    Core initialiser

    @type project_conf: dict
    @type core_conf: dict
    @type logger: logging.Logger

    @param project_conf: Configuration dictionnary containing name and paths
    @param core_conf: Configuration dictionnary for the core thread
    @param logger: The CIDE.py logger instance
    """

    self._project_name = project_conf['name']
    self._project_base_path = project_conf['base_dir']
    self._project_src_path = project_conf['code_dir']  # considered as root
    self._project_backup_path = project_conf['backup_dir']
    self._project_exec_path = project_conf['exec_dir']
    self._project_tmp_path = project_conf['tmp_dir']
    self._logger = logger

    # Make sure directories exists
    for project_dir in (self._project_base_path,
                        self._project_src_path,
                        self._project_backup_path,
                        self._project_exec_path,
                        self._project_tmp_path):
      if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    for node in os.listdir(self._project_tmp_path):
      if os.path.isfile(node):
        os.unlink(node)
      elif os.path.isdir(node):
        shutil.rmtree(node)

    # Asociation filepath -> (zoneTransit, set(userlist))
    # Recreate structure from existing files on disk
    self._project_files = dict()
    existing_files_path = get_existing_files(self._project_src_path)
    for path in existing_files_path:
      with open(os.path.join(self._project_src_path, path.lstrip('/')), 'r') as f:
        self._project_files[path] = self._create_file(f.read())

    self._core_listeners = list()  # List for direct indexing

    # Initialize first strategy to null since nobody is registered
    first_strategy = StrategyCallEmpty(self._change_core_strategy)
    self._core_listeners_strategy = first_strategy

    self.tasks = Queue()
    self._thread = CoreThread(self, core_conf)

  """
  Sync Call
  The call completes the task and returns with the result, if any
  """

  def start(self):
    """
    Start the application
    """
    self._thread.start()

  def stop(self):
    """
    Stop the application
    """
    self._thread.stop()

  def get_project_name(self):
    """
    Get the project name
    """
    return self._project_name

  def add_file(self, path):
    """
    Adds a file to the project tree

    @type path: str

    @param path: The path of the new file to be added in the project tree
    """
    # XXX Currently Unused
    # XXX Concurency issue without lock here
    if path not in self._project_files:
      self._project_files[path] = self._create_file()

  def delete_file(self, path):
    """
    Removes a file to the project tree

    @type path: str

    @param path: The path of the file to be removed in the project tree
    """
    # XXX Currently Unused
    # XXX Concurency issue without lock here
    if path in self._project_files:
      del self._project_files[path]

  def _add_task(self, f, *args):
    """
    Add a task into the task list

    @type f: function

    @param f: The task
    @param args: The arugments to be applied on f
    """
    self.tasks.put(Core.Task(f, args))

  def _create_file(self, content=""):
    """
    Creates the representation of a file
    Construction isolated in a function to simply further changes

    @type content: str

    @param content: The initial content of the file representation

    @return FileUserPair namedtuple
    """
    return self.FileUserPair(EditBuffer(content), set())

  """
  Async Call
  The call queues the task.
  If there's a result to receive, the caller must have the callback for it
  """
  def get_project_nodes(self, caller):
    """
    Get all files and directories from project

    @param caller: Username of the client to answer to

    List of nodes is: list((str, bool)) [(<<Project node>>, <<Node is directory flag>>)]
    Callback will be called with: nodes, caller
    """
    self._add_task(self._task_get_project_nodes, caller)
    self._logger.info("get_project_nodes task added")

  def get_file_content(self, path, caller):
    """
    Get the content of a file

    @type path: str
    @type caller: str

    @param path: The path of the file in the project tree
    @param caller: Username of the client to answer to

    Callback will be called with: tuple (<<File name>>, <<File Content>>, <<File Version>>), caller
    """
    self._add_task(self._task_get_file_content, path, caller)
    self._logger.info("get_file_content task added")

  def open_file(self, user, path):
    """
    Register a user to a file in order to receive file modification
    notifications. When the file does not exists, it is created

    @type user: str
    @type path: str

    @param user: The user name
    @param path: The path of the file to be registered to
    """
    self._add_task(self._task_open_file, user, path)
    self._logger.info("open_file task added")

  def unregister_user_to_file(self, user, path):
    """
    Unregister a user to a file in order to stop receiving file modification
    notifications

    @type user: str
    @type path: str

    @param user: The user name
    @param path: The path of the file to be unregistrered from
    """
    self._add_task(self._task_unregister_user_to_file, user, path)
    self._logger.info("unregister_user_to_file task added")

  def unregister_user_to_all_files(self, user):
    """
    Unregister a user from all files in order to stop receiving file modification
    notifications

    @type user: str

    @param user: The user name
    """
    self._add_task(self._task_unregister_user_to_all_files, user)
    self._logger.info("unregister_user_to_all_files task added")

  def file_edit(self, path, changes, caller):
    """
    Send changes, text added or text removed, to the file

    @type path: str
    @type changes: list [Change namedtuple]
    @type caller: str

    @param path: The path of the file in the project tree
    @param changes: Changes to be applied on the file
    @param caller: The author of the changes
    """
    self._add_task(self._task_file_edit, path, changes, caller)
    self._logger.info("File_edit task added")

  def create_archive(self, path, caller):
    """
    Compress all files under a project directory

    @type path: str
    @type caller: str

    @param path: The project directory path to compress
    @param caller: The user name


    @return: Queue on which the first element will be the path to the archive
    """
    synchrone_future = Queue()
    self._add_task(self._task_create_archive, path, caller, synchrone_future)
    self._logger.info("Create archive task added")
    return synchrone_future

  """
  Tasks call section
  Those are queued to be executed by the CoreThread
  """
  @task_time(microseconds=1)
  def _task_get_project_nodes(self, caller):
    """
    Task to get all files and directories from project

    @param caller: Username of the client to answer to

    Callback called: notify_get_project_nodes
    List of nodes is: list((str, bool)) [(<<Project node>>, <<Node is directory flag>>)]
    Callback will be called with: nodes, caller
    """
    sorted_nodes = self._impl_get_project_nodes()
    self._notify_event(lambda l: l.notify_get_project_nodes(sorted_nodes, caller))

  @task_time(microseconds=1)
  def _task_get_file_content(self, path, caller):
    """
    Task to get the content of a file

    @type path: str
    @type path: caller

    @param path: The path of the file in the project tree
    @param caller: Username of the client to answer to

    Callback will be called with: tuple (<<File name>>, <<File Content>>, <<File Version>>)
    """
    result = self._impl_get_file_content(path)
    self._notify_event(lambda l: l.notify_get_file_content(result, caller))

  @task_time(microseconds=1)
  def _task_open_file(self, user, path):
    """
    Task to register a user to a file in order to receive file modification
    notifications. When the file does not exists, it is created

    @type user: str
    @type path: str

    @param user: The user name
    @param path: The path of the file to be registered to
    """
    if path not in self._project_files:
      # Create file when does not exists
      self._project_files[path] = self._create_file()

    # Register user
    self._project_files[path].users.add(user)

    # Return content
    result = self._impl_get_file_content(path)
    self._notify_event(lambda l: l.notify_get_file_content(result, user))

  @task_time(microseconds=1)
  def _task_unregister_user_to_file(self, user, path):
    """
    Task to unregister a user to a file in order to stop receiving file modification
    notifications

    @type user: str
    @type path: str

    @param user: The user name
    @param path: The path of the file to be unregistrered from
    """
    if path in self._project_files:
      self._project_files[path].users.discard(user)

  @task_time(microseconds=1)
  def _task_unregister_user_to_all_files(self, user):
    """
    Task to unregister a user from all files in order to stop receiving file modification
    notifications

    @type user: str

    @param user: The user name
    """
    for f in self._project_files.itervalues():
      f.users.discard(user)

  @task_time(microseconds=1)
  def _task_file_edit(self, path, changes, user):
    """
    Task to add change to be applied to a file

    @type path: str
    @type changes: [namedtuple Change]
    @type user: str

    @param path: The path of the file in the project tree
    @param changes: Changes to be applied on the file
    @param user: User who sent the changes
    """
    author = user.encode("utf-8")
    if path in self._project_files:
      bundle = Modifications()
      bundle.extend([(EditAdd(c.pos, c.data.encode("utf-8"), author) if c.is_add
                      else EditRemove(c.pos, c.data, author)) for c in changes])
      self._project_files[path].file.add(bundle)

  @task_time(microseconds=1)
  def task_check_apply_notify(self):
    """
    Periodic task to apply pending modifications on all file from project.
    It also sends notifications uppon change application.
    """
    for (filepath, element) in self._project_files.iteritems():
      if not element.file.isEmpty():
        self._inner_task_apply_changes(filepath)

  # Does not need the task_time decorator since it is called from a task
  def _inner_task_apply_changes(self, path):
    """
    Partial task body to apply pending modifications on the file

    @type path: str

    @param path: The path of the file on which modifications will be applied
    """
    try:
      if path in self._project_files:
        version, changes = self._project_files[path].file.writeModifications()
        users_registered = deepcopy(self._project_files[path].users)

        # Notify registered users
        self._notify_event(
          lambda l: l.notify_file_edit(path,
                                       changes,
                                       version,
                                       users_registered))
    except:
      e = sys.exc_info()
      # XXX Remove after correction! C++ Should handle this!
      self._logger.exception("EXCEPTION RAISED {0}\n{1}\n{2}".format(e[0], e[1], e[2]))

  @task_time(microseconds=1)
  def _task_create_archive(self, path, caller, response):
    """
    Task to create an archive of the files under a project directory

    @type path: str
    @type caller: str
    @type response: Queue.Queue

    @param path: The path of the directory to compress
    @param caller: The user name
    @param response: Synchrone helper on which response needs to be written
    """
    archive_name = "{0}-{1}.zip".format(self.get_project_name(), caller)
    archive_path = os.path.join(self._project_tmp_path, archive_name)

    tempfile_prefix = "{0}-tmp".format(caller)
    archive_root_dir = "/{0}".format(path.split("/")[-1] or self.get_project_name())

    archive_nodes = (node
                     for (node, is_dir) in self._impl_get_project_nodes()
                     if not is_dir and node.startswith(path))

    with ZipFile(archive_path, "w") as zf:
      for filenode in archive_nodes:
        with NamedTemporaryFile(prefix=tempfile_prefix, dir=self._project_tmp_path) as ntf:
          # Not reading from disk to get the lastest version
          _, content, _ = self._impl_get_file_content(filenode)
          ntf.write(content)
          ntf.flush()  # Make sure text gets writen

          # Creates file into any needed parent directories
          zf.write(ntf.name, archive_root_dir + filenode)

    # Export file
    response.put(archive_path)

  """
  Implementation of tasks without communication overhead.
  This allows to reuse blocks of code
  """

  def _impl_get_project_nodes(self):
    sorted_nodes = ([(d, True) for d in get_existing_dirs(self._project_src_path)] +
                    [(f, False) for f in self._project_files.keys()])
    sorted_nodes.sort()
    return sorted_nodes

  def _impl_get_file_content(self, path):
    result = None
    if path in self._project_files:
      result = (path,
                self._project_files[path].file.content,
                0)  # Version
    return result

  """
  Observer and Stategy design patterns
  Handle event notifications to registered objects

  The listener will need to implement the following functions :
   - notify_file_edit(filename, changes, version, users)
   - notify_get_project_nodes(nodes_list)
   - notify_get_file_content(nodes_list)
  """

  def register_application_listener(self, listener):
    """
    Registers the listener to any events of the application

    @param listener: The observer requesting notifications from the app
    """
    if listener not in self._core_listeners:
      self._core_listeners.append(listener)
      self._core_listeners_strategy.upgrade_strategy()

  def unregister_application_listener(self, listener):
    """
    Unregisters the listener to stop receiving event notifications from the app

    @param listener: The observer requesting notifications from the application
    """
    if listener in self._core_listeners:
      self._core_listeners.remove(listener)
      self._core_listeners_strategy.downgrade_strategy()

  def _change_core_strategy(self, strategy):
    """
    Change the current strategy

    @param strategy: The new strategy to use
    """
    self._core_listeners_strategy = strategy

  def _notify_event(self, f):
    """
    Transfers an event to all application listeners using the current strategy

    @type f: callable

    @param f: The notification callable
    """
    self._core_listeners_strategy.send(f, self._core_listeners)


class CoreThread(Thread):
  """
  Core app Thread
  """

  def __init__(self, app, conf):
    """
    @type app: core.Core
    @type conf: dict

    @param app: The core application
    @param conf: Configuration dictionnary for realtime
    """
    Thread.__init__(self)
    # Alias for shorter name
    self._c_a_n = app.task_check_apply_notify
    self._tasks = app.tasks
    self._stop_asked = False

    cycle_time = conf["cycle_time"]
    critical_time = conf["buffer_critical"] / 100.0 * cycle_time
    secondary_time = conf["buffer_secondary"] / 100.0 * cycle_time
    auxiliary_time = conf["buffer_auxiliary"] / 100.0 * cycle_time

    self._cycle_time = timedelta(microseconds=cycle_time)
    self._time_buffer_critical = timedelta(microseconds=critical_time)
    self._time_buffer_secondary = timedelta(microseconds=secondary_time)
    self._time_buffer_auxiliary = timedelta(microseconds=auxiliary_time)

  def stop(self):
    self._stop_asked = True

  def run(self):
    none_critical_time_buffer = self._time_buffer_secondary+self._time_buffer_auxiliary

    # Define the ending point in time of the cycle
    # Tasks will be executed in the following order : auxiliary, secondary, critical
    # Therefore, end time points are defined corresponding to this order
    time_end_none_critical = datetime.now() + none_critical_time_buffer
    time_end_critical = time_end_none_critical + self._time_buffer_critical

    while not self._stop_asked:

      # None critical tasks
      # Execute loop until the time buffer exceeds
      while datetime.now() < time_end_none_critical:
        try:
          # Blocking until timeout or an available task allows lower CPU intensive work
          # Without blocking, CPU usage raises a lot and reduce CPU time for incomming requests
          available_block_time = time_end_none_critical - datetime.now()
          task = self._tasks.get(block=True, timeout=available_block_time.total_seconds())

          # Execute only if the task will not exceed the time buffer
          # Suppose that task were decorated by task_time function decorator
          if datetime.now() + task.f.time < time_end_none_critical:
            task.f(*task.args)
          else:
            # Since there is not enough time left, replace task back in queue
            # and proceed to other category of tasks.
            # Since order in task list is irrelevant, putting task at the end does not matter
            self._tasks.put(task)
            break

        # There were no tasks available
        except EmptyQueue:
          pass

      # Critical tasks
      # Check if executing the task will exceed the time buffer
      if datetime.now() + self._c_a_n.time < time_end_critical:
        self._c_a_n()
      else:
        print "CoreThread WARNING :: Not enough time to call task_check_apply_notify"

      # Increment rather than affecting to preserve any
      # unused or  overused time from last cycle
      time_end_none_critical += self._cycle_time
      time_end_critical += self._cycle_time
