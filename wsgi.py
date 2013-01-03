#!/usr/bin/env python

# NEXT: display count of how many checksum ok and how many fail
# NEXT: serve service/service_name as health_check
# NEXT: do it for mysql

import time
import sys
import os
import json
from flask import Flask, Request, Response
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
    return os.environ.get("VCAP_SERVICES", "{}")

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

@app.route('/old/mongo')
def mongotest():
    from pymongo import Connection
    uri = mongodb_uri()
    conn = Connection(uri)
    coll = conn.db['ts']
    coll.insert(dict(now=int(time.time())))
    last_few = [str(x['now']) for x in coll.find(sort=[("_id", -1)], limit=10)]
    body = "\n".join(last_few)
    return Response(body, content_type="text/plain;charset=UTF-8")

@app.route('/old/mongo')
def mongodb_uri():
    local = os.environ.get("MONGODB", None)
    if local:
        return local
    services = json.loads(os.environ.get("VCAP_SERVICES", "{}"))
    if services:
        creds = services['mongodb-1.8'][0]['credentials']
        uri = "mongodb://%s:%s@%s:%d/%s" % (
            creds['username'],
            creds['password'],
            creds['hostname'],
            creds['port'],
            creds['db'])
        print >> sys.stderr, uri
        return uri
    else:
        return "No services configured"
    

if __name__ == '__main__':
    app.run(debug=True)
