import hashlib
import pickle
import shelve

class cachedfunction(object):
    def __init__(self, func, cachefile):
        self.func=func
        self.cache = shelve.open(cachefile)
        
 
    def __call__(self, *args, **args2):
        s= hashlib.md5(self.func.__code__.co_code).hexdigest() \
        +hashlib.md5(pickle.dumps(args)).hexdigest() \
        +hashlib.md5(pickle.dumps(args2)).hexdigest()
        callhash=hashlib.md5(s.encode('utf-8')).hexdigest()
    
        if callhash in self.cache:
            return pickle.loads(self.cache[callhash])
        else:
            value = self.func(*args, **args2)
            self.cache[callhash] = pickle.dumps(value)
            return value
            
    def __del__(self):
        self.cache.close()