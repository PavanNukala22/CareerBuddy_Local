# Use PyMySQL as a drop-in for mysqlclient. The native _mysql.pyd DLL is
# blocked by Windows Application Control on this machine; PyMySQL is pure
# Python and avoids that block.
import pymysql
pymysql.install_as_MySQLdb()
