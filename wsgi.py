#!/usr/bin/env python

# NEXT: display count of how many checksum ok and how many fail
# NEXT: serve service/service_name as health_check

import time
import sys
import os
import json
from flask import Flask, Request, Response
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.orm import mapper, clear_mappers

application = app = Flask('wsgi')

@app.route('/')
def welcome():
    return "db tester\n"

@app.route('/routes')
def routes():
    services = json.loads(os.environ.get("VCAP_SERVICES", "{}"))
    avail_routes = ""
    for service in services:
        i = 0
        for s_id in services[service]:
            # name
            name = 'ERROR getting name from service'
            if 'name' in s_id:
                name = s_id['name']
            avail_routes += "{0} [{1}]: /service/{2}\n".format(service, i, name)
            i += 1
    return avail_routes

@app.route('/env')
def env():
    ret = ''
    ret += 'VCAP_SERVICES   : ' + os.environ.get("VCAP_SERVICES", "{}") + '\n'
    ret += 'VCAP_APP_PORT   : ' + os.environ.get("VCAP_APP_PORT", "{}") + '\n'
    ret += 'VCAP_APPLICATION: ' + os.environ.get("VCAP_APPLICATION", "{}") + '\n'
    return ret

@app.route('/service/<service_name>')
def show_service(service_name):
    curr_service = get_service_instance(service_name)
    if curr_service:
        return curr_service.summary()
    else:
        return "ERROR, who knows what happened"

@app.route('/service/<service_name>/create/<chunks>/<size>')
def create_service_data(service_name, chunks, size):
    curr_service = get_service_instance(service_name)
    if curr_service:
        return curr_service.create(chunks, size)
    else:
        return "ERROR, who knows what happened"

@app.route('/service/<service_name>/delete')
def delete_service_data(service_name):
    curr_service = get_service_instance(service_name)
    if curr_service:
        return curr_service.delete()
    else:
        return "ERROR, who knows what happened"

def get_service_instance(service_name):
    services = json.loads(os.environ.get("VCAP_SERVICES", "{}"))
    for service in services:
        for s_id in services[service]:
            if 'name' in s_id and s_id['name'] == service_name:
                if 'tags' in s_id:
                    if 'mongodb' in s_id['tags']:
                        return hammer_mongo(s_id)
                    elif 'mysql' in s_id['tags']:
                        return hammer_mysql(s_id)
                    elif 'future' in s_id['tags']:
                        return hammer(s_id)
    return None


def checksum(data):
    import md5
    import base64
    m = md5.new(data)
    return base64.b64encode(m.digest())


class hammer:
    def __init__(self, info):
        self.info = info

    def create(self, chunks, size):
        return "supposed to create {0} chunks of size {1}\n".format(chunks, size)

    def delete(self):
        return "deleting all data\n"

    def summary(self):
        return "generic summary: {0}\n".format(self.info)


class hammer_mongo(hammer):
    def connect(self):
        from pymongo import Connection
        uri = self.info['credentials']['url']
        conn = Connection(uri)
        return conn.db['hammer_mongo']

    def create(self, chunks, size):
        size = int(size)
        chunks = int(chunks)
        coll = self.connect()
        for c in range(chunks):
            import string
            import random
            rand_chars = ''.join(random.choice(string.ascii_letters+string.digits) for x in range(size))
            coll.insert(dict(now=int(time.time()), data=rand_chars, size=size, checksum=checksum(rand_chars)))
        return "created {0} chunks of size {1}\n".format(chunks, size)

    def delete(self):
        coll = self.connect()
        coll.drop()
        return "deleted all data\n"

    def summary(self):
        coll = self.connect()
        last_few = [(x['_id'], checksum(x['data']) == x['checksum']) for x in coll.find(sort=[("_id", -1)])]
        body = "\n".join([str(i[0]) + ' ' + str(i[1]) for i in last_few])
        return Response(body, content_type="text/plain;charset=UTF-8")
        #return "mongo summary: {0}\n".format(self.info)

# model for data to checksum
class HammerEntry(object):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(80), unique=True)
#    email = db.Column(db.String(120), unique=True)

    def __init__(self, now, size, checksum, data):
        self.now = now
        self.size = size
        self.checksum = checksum
        self.data = data

    def __repr__(self):
        return '<User %r>' % self.checksum

# kind of a hack...
class hammer_mysql(hammer):
    def connect(self):
        c = self.info['credentials']
        conn_string = 'mysql+oursql://{2}:{3}@{0}:{1}/{4}'.format(c['host'], c['port'], c['user'], c['password'], c['name'])
        self.engine = create_engine(conn_string, convert_unicode=True)
        self.db_session = scoped_session(sessionmaker(bind=self.engine))

        self.metadata = MetaData()

        self.hammerEntry = Table('hammer_mysql', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('now', Integer, unique=False),
            Column('size', Integer, unique=False),
            Column('checksum', String(50), unique=False),
            Column('data', String(1073741824), unique=False)
        )

        clear_mappers()
        mapper(HammerEntry, self.hammerEntry)

        # ensure tables exist
        self.metadata.create_all(bind=self.engine)

        return self.db_session

    def create(self, chunks, size):
        size = int(size)
        chunks = int(chunks)
        session = self.connect()
        #db
        for c in range(chunks):
            import string
            import random
            rand_chars = ''.join(random.choice(string.ascii_letters+string.digits) for x in range(size))
            entry = HammerEntry(int(time.time()), size, checksum(rand_chars), rand_chars)
            session.add(entry)
        session.commit()
        session.flush()
        session.close()
        return "created {0} chunks of size {1}\n".format(chunks, size)

    def delete(self):
        session = self.connect()
        self.hammerEntry.drop(self.engine)
        session.close()
        return "deleted all data\n"

    def summary(self):
        session = self.connect()
        last_few = [(x.id, checksum(x.data) == x.checksum) for x in session.query(HammerEntry).all()]
        body = "\n".join([str(i[0]) + ' ' + str(i[1]) for i in last_few])
        session.close()
        return Response(body, content_type="text/plain;charset=UTF-8")

if __name__ == '__main__':
    app.run(debug=True)
