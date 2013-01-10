af-db-tester
============

vcap database filling and checksumming, for migration testing.

```
➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org

db tester

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/routes

mongodb-1.8 [0]: /service/mongodb-723e6

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/service/mongodb-723e6

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/service/mongodb-723e6/create/8/1024

created 8 chunks of size 1024

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/service/mongodb-723e6

50e603eaad8b7071f9000007 True

50e603eaad8b7071f9000006 True

50e603eaad8b7071f9000005 True

50e603eaad8b7071f9000004 True

50e603eaad8b7071f9000003 True

50e603eaad8b7071f9000002 True

50e603eaad8b7071f9000001 True

50e603eaad8b7071f9000000 True

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/service/mongodb-723e6/delete

deleted all data

➜  af-db-tester git:(master) ✗ curl af-db-tester.vcap.example.org/service/mongodb-723e6

➜  af-db-tester git:(master) ✗
```

hope it's useful. cheers.
