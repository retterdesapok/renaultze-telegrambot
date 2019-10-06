import urllib.request
import json
import sqlite3


def main():
    da = DatabaseAccess()
    da.dumpUsersTable()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class DatabaseAccess:

    def __init__(self):
        self.conn = sqlite3.connect('renaultze.db')
        self.conn.row_factory = dict_factory
        self.ensureDatabaseExists()

    def ensureDatabaseExists(self):
        c = self.conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS users (userid INTEGER PRIMARY KEY, username, password, vin, tokenJson, lastApiResult);")

    def getUser(self, userid):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE userid = ?", [userid])
        return c.fetchone()

    def getUsers(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users")
        return c.fetchall()

    def insertUser(self, userid, username, password, vin, tokenJson):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO users (userid, username, password, vin, tokenJson, lastApiResult) VALUES (?, ?, ?, ?, ?, null)",
            [userid, username, password, vin, tokenJson])
        self.conn.commit()

    def updateApiResultForUser(self, userid, lastApiResult):
        c = self.conn.cursor()
        c.execute("UPDATE users SET lastApiResult = ? WHERE userid = ?", [lastApiResult, userid])
        self.conn.commit()

    def updateToken(self, userid, tokenJson):
        c = self.conn.cursor()
        c.execute("UPDATE users SET tokenJson = ? WHERE userid = ?", [tokenJson, userid])
        self.conn.commit()

    def deleteUser(self, userid):
        c = self.conn.cursor()
        c.execute("DELETE FROM users WHERE userid = ?", [userid])
        self.conn.commit()

    def dumpUsersTable(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users")
        for row in c.fetchall():
            print(row)


if __name__ == '__main__':
    main()
