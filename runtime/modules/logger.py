
def log(log, owner = None):
    logPrint(log, "", owner)

def logWarning(log, owner = None):
    logPrint(log, "WARNING", owner)

def logError(log, owner = None):
    logPrint(log, "ERROR", owner)

# internal
def logPrint(log, suffix, owner):

    output = ""
    if owner != None:
        output = str(type(owner))

    if len(suffix) > 0:
        output += " ["+suffix+"] "

    output += log

    print(output)
