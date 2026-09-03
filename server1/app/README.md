# app：服务器1 组装入口

本模块是**唯一**的 Spring Boot 启动模块。它不实现业务，只把 `gateway`、`auth`、`circulation`、`ingest`、`project`、`task`、`audit` 组装成一个进程。

## 启动

先确保本机 MySQL 已执行 `server1/sql` 下脚本，库名 `geo_server1`。

```bash
cd server1
mvn clean install -DskipTests
mvn -pl app spring-boot:run
```

默认端口：`8081`

数据库：`SERVER1_DB_HOST/PORT/USER/PASSWORD`，默认 `127.0.0.1:3306` / `root` / `123456`。

部署产物：`app/target/server1-app-0.1.0-SNAPSHOT.jar`
