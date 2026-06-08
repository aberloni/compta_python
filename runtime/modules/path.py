from modules.system import *

class Path:

    localDatabase = False
    shkExternal = "externals"

    def getLnkPath(pathLnk):
        if not pathLnk.endswith(".lnk"):
            pathLnk += ".lnk"
        absPath = getExtractShkPath(pathLnk)
        return absPath

    @staticmethod
    def getExternalPath():
        import configs
        if configs.testMode:
            return configs.testDbPath
        return Path.getLnkPath(Path.shkExternal)

    @staticmethod
    def getDbPath():
        return Path.getExternalPath() + "database/"

    @staticmethod
    def getExportFolderPath():
        return Path.getExternalPath() + "exports/"

    @staticmethod
    def getExportBillingPath():
        return Path.getExportFolderPath() + "billings/"

    @staticmethod
    def getLinesFromDbType(dbType, fileNameExt):
        path = Path.getDbTypePath(dbType)
        path += fileNameExt
        return loadFileUTF(path)

    @staticmethod
    def getDbTypePath(dbType):
        return Path.getDbPath() + dbType.name + "/"

    @staticmethod
    def getLinesDbFile(fileNameExt):
        path = Path.getDbPath()
        path += fileNameExt
        return loadFileUTF(path)

    @staticmethod
    def getAllFilesFromLnk(absPathLnk):
        path = Path.getLnkPath(absPathLnk)
        return getAllFilesInFolder(path)

    @staticmethod
    def getAllFilesFromDbType(dbType):
        path = Path.getDbTypePath(dbType)
        return getAllFilesInFolder(path)
