
def log(log, owner):
    logPrint(log, owner)

def logWarning(log, owner):
    logPrint(log, "WARNING", owner)

def logError(log, owner):
    logPrint(log, "ERROR", owner)

def logPrint(log, owner):
    logPrint(log, "", owner)

# internal
def logPrint(log, suffix, owner):
    
    if owner != None: 
        output = str(type(owner))
    
    if len(suffix) > 0:
        output += " ["+suffix+"] "
        
    output += log
    
    print(output)