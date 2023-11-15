import configs
import os


def filterLines(lines):

    output = []
    for l in lines:
        
        l = l.strip()

        if len(l) <= 0:
            #print("skipping empty line")
            continue

        if "#" in l:
            #print("skipping comment line")
            continue

        output.append(l)

    return output

"""
load using lnk filtering
"""
def loadFileLnk(lnk, fileNameExt):
    
    from library.path import Path
    
    # regen real path of where the file is
    path = Path.getLnkPath(lnk)

    return loadFile(path+fileNameExt)

"""
just load a file from database/ folder
"""
def loadFileDb(fileNameExt):
    from library.path import Path
    path = Path.pathDatabase + fileNameExt
    return loadFile(path)

def loadFile(path):

    if not os.path.exists(path):
       print("[WARNING] file @ "+path+" does not exists")
       return None
    
    #print("reading file @ "+path)

    with open(path, "r") as f:
        lines = f.readlines()
    
    return filterLines(lines)

"""
load all lines of a file
in : abs path to file /w ext
"""
def loadFileUTF(path):

    if not os.path.exists(path):
       print("[WARNING] file @ "+path+" does not exists")
       return None
    
    #print(path)

    with open(path, "r", encoding='utf-8') as f:
        lines = f.readlines()

    return filterLines(lines)

"""
load a file from db type folders
"""
def loadFileByDbType(dbType, fileNameExt):
    from path import Path
    path = Path.getDbTypePath(dbType)+"_"+fileNameExt

    f = open(path, "r")
    lines = f.readlines()

    # Strips the newline character
    for i in range(0, len(lines)):
        lines[i] = lines[i].strip()
    
    # string[]
    return lines

"""
input : path that includes file.lnk
"""
def getExtractShkPath(path):
    import struct

    #path = 'myfile.txt.lnk'

    target = ''

    with open(path, 'rb') as stream:
        content = stream.read()
        # skip first 20 bytes (HeaderSize and LinkCLSID)
        # read the LinkFlags structure (4 bytes)
        lflags = struct.unpack('I', content[0x14:0x18])[0]
        position = 0x18
        # if the HasLinkTargetIDList bit is set then skip the stored IDList 
        # structure and header
        if (lflags & 0x01) == 1:
            position = struct.unpack('H', content[0x4C:0x4E])[0] + 0x4E
        last_pos = position
        position += 0x04
        # get how long the file information is (LinkInfoSize)
        length = struct.unpack('I', content[last_pos:position])[0]
        # skip 12 bytes (LinkInfoHeaderSize, LinkInfoFlags, and VolumeIDOffset)
        position += 0x0C
        # go to the LocalBasePath position
        lbpos = struct.unpack('I', content[position:position+0x04])[0]
        position = last_pos + lbpos
        # read the string at the given position of the determined length
        size= (length + last_pos) - position - 0x02
        temp = struct.unpack('c' * size, content[position:position+size])
        target = ''.join([chr(ord(a)) for a in temp])
    
    return target+"/"

"""
out : array of files within that folder
"""
def getAllFilesInFolder(absPath):
    
    # https://stackoverflow.com/questions/3207219/how-do-i-list-all-files-of-a-directory

    import glob

    files = glob.glob(absPath+"*")

    #print(files)
    
    return files


def log(log):
    print(log)

def warning(log):
    print("     [WARNING] "+log)

def error(log):
    print("     [ERROR] "+log)
