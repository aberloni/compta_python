from modules.system import *

class Path:

    localDatabase = False

    shkExternal = "externals"
    #shkDatabase = "database"
    #shkExport = "exports"

    # in : abs path to lnk
    # out : abs path
    def getLnkPath(pathLnk):
        
        if not pathLnk.endswith(".lnk"):
            pathLnk += ".lnk"

        absPath = getExtractShkPath(pathLnk)

        #print(pathLnk)
        #print(absPath)

        return absPath

    @staticmethod
    def getDbPath():
        return Path.getLnkPath(Path.shkExternal)+"database/"
    
    """
    out : path to exports/ from db/lnk
    """
    @staticmethod
    def getExportFolderPath():
        return Path.getLnkPath(Path.shkExternal)+"exports/"
    
    @staticmethod
    def getExportBillingPath():
        return Path.getExportFolderPath()+"billings/"
    

    """
    all files made by hand
    """
    @staticmethod
    def getLinesFromDbType(dbType, fileNameExt):
        path = Path.getDbTypePath(dbType)
        path += fileNameExt
        return loadFileUTF(path)
    
    """
    in : lnk name within database path
    out : abs path
    """
    @staticmethod
    def getDbTypePath(dbType):
        return Path.getDbPath() + dbType.name+"/"
    
    @staticmethod
    def getLinesDbFile(fileNameExt):
        path = Path.getDbPath()
        path += fileNameExt
        return loadFileUTF(path)
    
    @staticmethod
    def getAllFilesFromLnk(absPathLnk):
        
        # returns the actual folder path of that link
        path = Path.getLnkPath(absPathLnk)

        return getAllFilesInFolder(path)

    @staticmethod
    def getAllFilesFromDbType(dbType):
        
        # returns the actual folder path of that link
        path = Path.getDbTypePath(dbType)
        
        #print("fetching files @"+path)

        return getAllFilesInFolder(path)
