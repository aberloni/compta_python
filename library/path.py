class Path:

    localDatabase = False

    shkExternal = "externals"
    #shkDatabase = "database"
    #shkExport = "exports"

    # in : abs path to lnk
    # out : abs path
    def getLnkPath(pathLnk):
        import library.system
        
        if not pathLnk.endswith(".lnk"):
            pathLnk += ".lnk"

        absPath = library.system.getExtractShkPath(pathLnk)

        #print(pathLnk)
        #print(absPath)

        return absPath

    # in : dbType
    # out : abs path to database/type/
    @staticmethod
    def getPathDbType(dbType):
        return Path.getDbTypePath(dbType.name)
    
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
        import library.system
        path = Path.getDbTypePath(dbType)
        path += fileNameExt
        return library.system.loadFileUTF(path)
    
    """
    in : lnk name within database path
    out : abs path
    """
    def getDbTypePath(dbType):
        return Path.getDbPath() + dbType.name+"/"
    
    @staticmethod
    def getLinesDbFile(fileNameExt):
        import library.system
        path = Path.getDbPath()
        path += fileNameExt
        return library.system.loadFileUTF(path)
    
    """
    exported from bank website
    """
    @staticmethod
    def getLinesFromStatement(fileNameExt):
        from library.database import DatabaseType
        import library.system
        
        path = Path.getDbTypePath(DatabaseType.statements)
        path += fileNameExt

        #print("lines from @ "+path)

        return library.system.loadFile(path)
    

    @staticmethod
    def getAllFilesFromLnk(absPathLnk):
        import library.system
        
        # returns the actual folder path of that link
        path = Path.getLnkPath(absPathLnk)

        return library.system.getAllFilesInFolder(path)

    @staticmethod
    def getAllFilesFromDbType(dbType):
        import library.system
        
        # returns the actual folder path of that link
        path = Path.getDbTypePath(dbType)
        
        #print("fetching files @"+path)

        return library.system.getAllFilesInFolder(path)



    @staticmethod
    def getExportStatementsFolder():
        return Path.getExportFolderPath()+"statements/"

    @staticmethod
    def getExportBillingFolder():
        return Path.getExportFolderPath()+"billings/"
