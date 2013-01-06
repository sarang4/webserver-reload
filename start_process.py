import os
import sys
import time
import signal
import threading
import atexit
import Queue
import subprocess
import glob

_interval = 1.0
_times = {}
_files = []

_running = False
_queue = Queue.Queue()
_lock = threading.Lock()

def _restart(path):
    _queue.put(True)
    prefix = 'monitor (pid=%d):' % os.getpid()
    print >> sys.stderr, '%s Change detected to \'%s\'.' % (prefix, path)
    print >> sys.stderr, '%s Triggering process restart.' % prefix
    os.kill(os.getpid(), signal.SIG_IGN)

def _modified(path):
    try:
        # If path doesn't denote a file and were previously
        # tracking it, then it has been removed or the file type
        # has changed so force a restart. If not previously
        # tracking the file then we can ignore it as probably
        # pseudo reference such as when file extracted from a
        # collection of modules contained in a zip file.

        if not os.path.isfile(path):
            return path in _times

        # Check for when file last modified.

        mtime = os.stat(path).st_mtime
	if path not in _times:
            _times[path] = mtime
	
        # Force restart when modification time has changed, even
        # if time now older, as that could indicate older file
        # has been restored.

        if mtime != _times[path]:
            return True
    except:
        # If any exception occured, likely that file has been
        # been removed just before stat(), so force a restart.
        return True

    return False

def _monitor():

    while 1:
        # Check modification times on files which have
        # specifically been registered for monitoring.

	for path in _files:
	    if _modified(path):
		return _restart(path)

        # Go to sleep for specified interval.
	time.sleep(_interval)
	try:
	    return _queue.get(timeout=_interval)
	except:
	    pass

_thread = threading.Thread(target=_monitor)
_thread.setDaemon(True)

def _exiting():
    try:
	_queue.put(True)
    except:
	pass
    _thread.join()

atexit.register(_exiting)

def track(directory_path):
    for path in glob.glob('%s/*' %directory_path):
	if os.path.isdir(path):
	    track(path)
	elif not path in _files:
	    _files.append(path)

def start(interval=1.0, directory_path = os.path.dirname(os.path.abspath(__file__))):
    global _interval
    _interval = interval
    global _running
    _lock.acquire()
    if not _running:
        prefix = 'monitor (pid=%d):' % os.getpid()
        print >> sys.stderr, '%s Starting change monitor.' % prefix
        _running = True
	track(directory_path)
	_thread.start()
    _lock.release()


