import configs
import os

# return the real path of a LNK target
#
def getSubdirPath(sub):

    # path to LNK from database sub name
    path = configs.pathDatabase + sub.name
    path += ".lnk"

    return getExtractShkPath(path)

# load using lnk filtering
#
def loadFileLnk(sub, fileNameExt):
    
    # regen real path of where the file is
    path = getSubdirPath(sub)

    path += fileNameExt

    # print("LNK:PATH:", path)

    return loadFile(path)

# just load from database/ folder
#
def loadFileDb(fileNameExt):

    path = configs.pathDatabase + fileNameExt

    return loadFile(path)

# 
# load a file from the database folder
# 
def loadFile(pathFileNameExt):

    path = pathFileNameExt

    if not os.path.exists(path):
       return None
     
    with open(path, "r", encoding='utf-8') as f:
        lines = f.readlines()

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

def loadFileByDbType(dbType, fileNameExt):
    
    path = configs.pathDatabase+dbType.name+"_"+fileNameExt

    f = open(path, "r")
    lines = f.readlines()

    # Strips the newline character
    for i in range(0, len(lines)):
        lines[i] = lines[i].strip()
    
    # string[]
    return lines

# input : path that includes file.lnk
# 
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

def getExportFolderPath():
    return getExtractShkPath("exports.lnk")

def getAllFilesInFolder(path):
    
    # https://stackoverflow.com/questions/3207219/how-do-i-list-all-files-of-a-directory

    import glob

    files = glob.glob(path+"*")

    #print(files)
    
    return files

def getAllFilesFromLnk(pathLnk):

    # returns the actual folder path of that link
    path = getExtractShkPath(pathLnk)

    return getAllFilesInFolder(path)