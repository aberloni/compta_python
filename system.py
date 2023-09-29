import configs

def loadFile(fileNameExt):

    path = configs.pathDatabase + fileNameExt

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

